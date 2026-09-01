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
**Handlers must be idempotent** — see ``app/jobs/handlers/summarize_thread.py``.

Note the name collision with ``app.messages.send_message``: that one sends a
chat message to a thread, this one enqueues a background job. They are
unrelated.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

from sqlalchemy import case, func, insert, select, update

from app.db import Querier, query, tx
from app.schema import jobs

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


async def send_message(
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
    visible_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)

    async def write(q: Querier) -> SendResult:
        if deduplication_id:
            existing = await q(
                select(jobs.c.id)
                .where(jobs.c.deduplication_id == deduplication_id)
                .limit(1)
            )
            if existing.rows:
                return {"duplicate": True}

        inserted = await q(
            insert(jobs)
            .values(
                name=name,
                payload=payload,
                deduplication_id=deduplication_id,
                message_group_id=message_group_id,
                visible_after=visible_at,
            )
            .returning(jobs.c.id)
        )
        return {"id": int(inserted.rows[0]["id"])}

    return await tx(write)


async def receive_messages(
    max_messages: int = 1,
    visibility_timeout_ms: int = DEFAULT_VISIBILITY_TIMEOUT_MS,
) -> list[ReceivedJob]:
    """
    Claim up to ``max_messages`` visible jobs.

    Each candidate is claimed with a conditional UPDATE that only matches while
    the row is still ``queued``, so a job never goes to two workers: whoever
    loses the race simply sees zero rows updated and skips it.
    """
    hidden_until = datetime.now(UTC) + timedelta(milliseconds=visibility_timeout_ms)

    async def claim(q: Querier) -> list[ReceivedJob]:
        candidates = await q(
            select(jobs.c.id, jobs.c.name, jobs.c.payload, jobs.c.attempts)
            .where(jobs.c.status == "queued", jobs.c.visible_after <= func.now())
            .order_by(jobs.c.visible_after, jobs.c.id)
            .limit(max_messages)
        )

        claimed: list[ReceivedJob] = []
        for candidate in candidates.rows:
            handle = str(uuid.uuid4())
            updated = await q(
                update(jobs)
                .where(jobs.c.id == candidate["id"], jobs.c.status == "queued")
                .values(
                    status="in_flight",
                    attempts=jobs.c.attempts + 1,
                    receipt_handle=handle,
                    visible_after=hidden_until,
                    updated_at=func.now(),
                )
                .returning(jobs.c.id)
            )
            if updated.rows:
                claimed.append(
                    ReceivedJob(
                        id=int(candidate["id"]),
                        name=candidate["name"],
                        payload=candidate["payload"],
                        attempts=int(candidate["attempts"]) + 1,
                        receipt_handle=handle,
                    )
                )
        return claimed

    return await tx(claim)


async def delete_message(receipt_handle: str) -> None:
    """Ack a job: mark it done and retire its receipt handle."""
    await query(
        update(jobs)
        .where(jobs.c.receipt_handle == receipt_handle)
        .values(status="done", receipt_handle=None, updated_at=func.now())
    )


async def release_message(receipt_handle: str, reason: str | None = None) -> None:
    """
    Nack a job: make it visible again, or park it in ``failed`` once it has
    burned through ``max_attempts``.
    """
    await query(
        update(jobs)
        .where(jobs.c.receipt_handle == receipt_handle)
        .values(
            status=case(
                (jobs.c.attempts >= jobs.c.max_attempts, "failed"), else_="queued"
            ),
            receipt_handle=None,
            visible_after=func.now(),
            last_error=reason,
            updated_at=func.now(),
        )
    )
