"""
Thread domain layer.

A thread's patient is immutable. Every thread is owned by exactly one patient
(``threads.patient_id``) and that patient is fixed for the life of the thread:
there is no reassignment, no merge, and no "switch patient" operation. There
is deliberately **no ``set_thread_patient`` function** in this module, and one
should not be added — an inbound message that doesn't match the thread's
patient is a routing error to be surfaced, not a signal to mutate the thread.
See docs/PRODUCT.md.

A thread's *physicians*, by contrast, are a mutable set (``threads_physicians``).
"""

from __future__ import annotations

import uuid
from typing import Any, Iterable

from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Q, QuerySet

from core.clock import now_ms
from core.dto import ApiThread, ThreadMetadata, UserRole
from core.models import Message, Thread, ThreadPhysician
from core.users import resolve_role

DEFAULT_METADATA: ThreadMetadata = {
    "unrespondedPatientMessagesCount": 0,
    "lastSummaryGenerated": None,
    "topicTags": [],
    "priority": "normal",
}

THREAD_LIMIT = 100


def normalize_metadata(raw: Any) -> ThreadMetadata:
    """
    Coerce a stored ``metadata`` blob into a complete ThreadMetadata.

    The column is schemaless, so a row written before a key existed (or by
    something that dropped one) is filled in from the defaults rather than
    surfacing a partial dict to the frontend.
    """
    merged: dict[str, Any] = {**DEFAULT_METADATA}
    if isinstance(raw, dict):
        merged.update(raw)
    return ThreadMetadata(
        unrespondedPatientMessagesCount=merged["unrespondedPatientMessagesCount"],
        lastSummaryGenerated=merged["lastSummaryGenerated"],
        topicTags=merged["topicTags"],
        priority=merged["priority"],
    )


def to_api(thread: Thread) -> ApiThread:
    """
    Map a Thread row to its DTO.

    ``users`` is the participant list the UI renders: the patient first, then
    the care team. Expects ``thread_physicians`` to have been prefetched.
    """
    physician_ids = [tp.physician_id for tp in thread.thread_physicians.all()]
    return {
        "id": thread.id,
        "title": thread.title,
        "users": [thread.patient_id, *physician_ids],
        "date_created": thread.date_created,
        "metadata": normalize_metadata(thread.metadata),
    }


def _threads_with_physicians() -> QuerySet[Thread]:
    """Base queryset; prefetches the care team so `to_api` costs no extra query."""
    return Thread.objects.prefetch_related(
        Prefetch(
            "thread_physicians",
            queryset=ThreadPhysician.objects.order_by("added_at", "physician_id"),
        )
    )


def list_threads(search_query: str | None = None) -> list[ApiThread]:
    """
    The newest threads, optionally filtered by a free-text query that matches
    either the thread title or the body of any message in the thread.
    """
    threads = _threads_with_physicians()

    trimmed = (search_query or "").strip()
    if trimmed:
        # `icontains` escapes LIKE wildcards, so a typed `%` or `_` matches
        # literally instead of turning into a wildcard.
        matching_message = Message.objects.filter(
            thread=OuterRef("pk"), message__icontains=trimmed
        )
        threads = threads.filter(
            Q(title__icontains=trimmed) | Exists(matching_message)
        )

    return [to_api(t) for t in threads.order_by("-date_created")[:THREAD_LIMIT]]


def get_thread_by_id(thread_id: str) -> ApiThread | None:
    thread = _threads_with_physicians().filter(id=thread_id).first()
    return to_api(thread) if thread else None


def create_thread(title: str, user_ids: Iterable[str]) -> ApiThread:
    """
    Create a thread from a flat list of participant ids.

    Splits the ids into exactly one patient and zero-or-more physicians (by
    resolving each id's role) before persisting. This is the orchestration the
    UI calls into via the REST layer; the low-level insert lives in
    :func:`_insert_thread`.
    """
    patient_id: str | None = None
    physician_ids: list[str] = []

    for user_id in user_ids:
        role = resolve_role(user_id)
        if role == "patient":
            if patient_id and patient_id != user_id:
                raise ValueError("create_thread: a thread can only have one patient")
            patient_id = user_id
        else:
            physician_ids.append(user_id)

    if not patient_id:
        raise ValueError("create_thread: a thread must include exactly one patient")

    return _insert_thread(title, patient_id, physician_ids)


def _insert_thread(title: str, patient_id: str, physician_ids: list[str]) -> ApiThread:
    thread_id = str(uuid.uuid4())
    date_created = now_ms()

    with transaction.atomic():
        Thread.objects.create(
            id=thread_id,
            title=title,
            patient_id=patient_id,
            date_created=date_created,
        )
        ThreadPhysician.objects.bulk_create(
            [
                ThreadPhysician(thread_id=thread_id, physician_id=physician_id)
                for physician_id in dict.fromkeys(physician_ids)
            ],
            ignore_conflicts=True,
        )

    thread = get_thread_by_id(thread_id)
    if thread is None:
        raise RuntimeError(f"_insert_thread: insert vanished ({thread_id})")
    return thread


def get_thread_metadata(thread_id: str) -> ThreadMetadata:
    row = Thread.objects.filter(id=thread_id).values("metadata").first()
    if row is None:
        raise ValueError(f"get_thread_metadata: unknown thread {thread_id}")
    return normalize_metadata(row["metadata"])


def set_thread_metadata(thread_id: str, metadata: ThreadMetadata) -> None:
    Thread.objects.filter(id=thread_id).update(metadata=metadata)


def record_message_for_metadata(thread_id: str, role: UserRole) -> None:
    """
    Update a thread's unresponded-patient counter after a new message.

    Patient messages increment the count; a physician reply resets it to 0.
    This is the only place the counter moves — see docs/PRODUCT.md, "Inbound
    and the work queue".
    """
    metadata = get_thread_metadata(thread_id)
    metadata["unrespondedPatientMessagesCount"] = (
        metadata["unrespondedPatientMessagesCount"] + 1 if role == "patient" else 0
    )
    set_thread_metadata(thread_id, metadata)
