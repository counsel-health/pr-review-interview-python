"""
In-database job queue with an SQS-shaped interface.

The verbs and semantics intentionally mirror AWS SQS so this local primitive
maps 1:1 onto the real queue Counsel uses in production:

    send_message     -> enqueue a job (with an optional deduplication_id)
    receive_messages -> poll for jobs; returns up to N with a visibility timeout
    delete_message   -> ack a job via its receipt handle (success)
    release_message  -> nack early; the job becomes visible again

At-least-once delivery is real here: if a worker fails to call
:func:`delete_message` before the visibility timeout expires, the job becomes
visible again and another :func:`receive_messages` call will return it.
**Handlers must be idempotent** — see ``jobs/handlers/summarize_thread.py``.

Note the name collision with ``core.messages.send_message``: that one sends a
chat message to a thread, this one enqueues a background job. They are
unrelated.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, TypedDict

from django.db import transaction
from django.db.models import Case, F, Q, Value, When
from django.utils import timezone

from core.models import Job

DEFAULT_VISIBILITY_TIMEOUT_MS = 30_000


@dataclass(frozen=True)
class ReceivedJob:
    """A job claimed by a worker, along with the handle needed to ack it."""

    id: int
    name: str
    payload: Any
    attempts: int
    receipt_handle: str


class SendResult(TypedDict, total=False):
    """``{"id": n}`` for a fresh enqueue, ``{"duplicate": True}`` otherwise."""

    id: int
    duplicate: bool


def send_message(
    name: str,
    payload: Any,
    deduplication_id: str | None = None,
    message_group_id: str | None = None,
    delay_seconds: int = 0,
) -> SendResult:
    """
    Enqueue a job.

    When ``deduplication_id`` is supplied and a job already carries it, nothing
    is inserted and ``{"duplicate": True}`` comes back. The check and the
    insert share a transaction; the partial unique index ``jobs_dedup_idx`` is
    the backstop for two callers racing on the same id.
    """
    visible_at = timezone.now() + timedelta(seconds=delay_seconds)

    with transaction.atomic():
        if deduplication_id and Job.objects.filter(
            deduplication_id=deduplication_id
        ).exists():
            return {"duplicate": True}

        job = Job.objects.create(
            name=name,
            payload=payload,
            deduplication_id=deduplication_id,
            message_group_id=message_group_id,
            visible_after=visible_at,
        )
        return {"id": job.id}


def receive_messages(
    max_messages: int = 1,
    visibility_timeout_ms: int = DEFAULT_VISIBILITY_TIMEOUT_MS,
) -> list[ReceivedJob]:
    """
    Claim up to ``max_messages`` visible jobs.

    Each candidate is claimed with a conditional UPDATE that only matches while
    the row is still ``queued``, so a job never goes to two workers: whoever
    loses the race simply sees zero rows updated and skips it.
    """
    hidden_until = timezone.now() + timedelta(milliseconds=visibility_timeout_ms)

    with transaction.atomic():
        candidates = list(
            Job.objects.filter(
                status=Job.Status.QUEUED, visible_after__lte=timezone.now()
            )
            .order_by("visible_after", "id")
            .values("id", "name", "payload", "attempts")[:max_messages]
        )

        claimed: list[ReceivedJob] = []
        for candidate in candidates:
            handle = str(uuid.uuid4())
            updated = Job.objects.filter(
                id=candidate["id"], status=Job.Status.QUEUED
            ).update(
                status=Job.Status.IN_FLIGHT,
                attempts=candidate["attempts"] + 1,
                receipt_handle=handle,
                visible_after=hidden_until,
                updated_at=timezone.now(),
            )
            if updated:
                claimed.append(
                    ReceivedJob(
                        id=candidate["id"],
                        name=candidate["name"],
                        payload=candidate["payload"],
                        attempts=candidate["attempts"] + 1,
                        receipt_handle=handle,
                    )
                )
        return claimed


def delete_message(receipt_handle: str) -> None:
    """Ack a job: mark it done and retire its receipt handle."""
    Job.objects.filter(receipt_handle=receipt_handle).update(
        status=Job.Status.DONE,
        receipt_handle=None,
        updated_at=timezone.now(),
    )


def release_message(receipt_handle: str, reason: str | None = None) -> None:
    """
    Nack a job: make it visible again, or park it in ``failed`` once it has
    burned through ``max_attempts``.
    """
    Job.objects.filter(receipt_handle=receipt_handle).update(
        status=Case(
            When(
                Q(attempts__gte=F("max_attempts")),
                then=Value(Job.Status.FAILED.value),
            ),
            default=Value(Job.Status.QUEUED.value),
        ),
        receipt_handle=None,
        visible_after=timezone.now(),
        last_error=reason,
        updated_at=timezone.now(),
    )
