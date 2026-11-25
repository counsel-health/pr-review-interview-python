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

import json
import re
import uuid
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import func, insert, literal, literal_column, or_, select, update
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.clock import now_ms
from app.db import Querier, one, query, tx
from app.dto import ApiThread, ThreadMetadata
from app.schema import messages, threads, threads_physicians
from app.users import resolve_role

DEFAULT_METADATA = ThreadMetadata(
    unrespondedPatientMessagesCount=0,
    lastSummaryGenerated=None,
    topicTags=[],
    priority="normal",
)

THREAD_LIMIT = 100

#: The thread's care team, aggregated into one text[] on the thread's own row.
#: Doing it in the SELECT is what keeps `to_api` free: converting N threads to
#: DTOs costs one query, not one query per thread.
_PHYSICIAN_IDS = func.coalesce(
    func.array_agg(
        aggregate_order_by(
            threads_physicians.c.physician_id,
            threads_physicians.c.added_at,
            threads_physicians.c.physician_id,
        )
    ).filter(threads_physicians.c.physician_id.isnot(None)),
    literal_column("ARRAY[]::text[]"),
).label("physician_ids")

SELECT_WITH_PHYSICIANS = (
    select(
        threads.c.id,
        threads.c.title,
        threads.c.patient_id,
        threads.c.date_created,
        threads.c.metadata,
        _PHYSICIAN_IDS,
    )
    .select_from(
        threads.outerjoin(
            threads_physicians, threads_physicians.c.thread_id == threads.c.id
        )
    )
    .group_by(threads.c.id)
)


def normalize_metadata(raw: Any) -> ThreadMetadata:
    """
    Coerce a stored ``metadata`` blob into a complete ThreadMetadata.

    The column is schemaless, so a row written before a key existed (or by
    something that dropped one) is filled in from the defaults rather than
    surfacing a partial object to the frontend.
    """
    parsed = json.loads(raw) if isinstance(raw, str) else raw
    merged = DEFAULT_METADATA.model_dump()
    if isinstance(parsed, dict):
        merged.update(parsed)
    return ThreadMetadata.model_validate(merged)


def to_api(row: Mapping[str, Any]) -> ApiThread:
    """
    Map a thread row to its DTO.

    ``users`` is the participant list the UI renders: the patient first, then
    the care team. Expects the row to carry ``physician_ids``, which
    :data:`SELECT_WITH_PHYSICIANS` aggregates.
    """
    physician_ids: list[str] = list(row["physician_ids"] or [])
    return ApiThread(
        id=row["id"],
        title=row["title"],
        users=[row["patient_id"], *physician_ids],
        date_created=row["date_created"],
        metadata=normalize_metadata(row["metadata"]),
    )


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so a typed ``%`` or ``_`` matches literally."""
    return re.sub(r"([\\%_])", r"\\\1", value)


async def list_threads(search_query: str | None = None) -> list[ApiThread]:
    """
    The newest threads, optionally filtered by a free-text query that matches
    either the thread title or the body of any message in the thread.
    """
    statement = SELECT_WITH_PHYSICIANS

    trimmed = (search_query or "").strip()
    if trimmed:
        pattern = f"%{_escape_like(trimmed)}%"
        matching_message = (
            select(literal(1))
            .select_from(messages)
            .where(
                messages.c.thread_id == threads.c.id,
                messages.c.message.ilike(pattern, escape="\\"),
            )
            .exists()
        )
        statement = statement.where(
            or_(threads.c.title.ilike(pattern, escape="\\"), matching_message)
        )

    result = await query(
        statement.order_by(threads.c.date_created.desc()).limit(THREAD_LIMIT)
    )
    return [to_api(row) for row in result.rows]


async def get_thread_by_id(thread_id: str) -> ApiThread | None:
    row = await one(SELECT_WITH_PHYSICIANS.where(threads.c.id == thread_id))
    return to_api(row) if row else None


async def create_thread(title: str, user_ids: Iterable[str]) -> ApiThread:
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
        role = await resolve_role(user_id)
        if role == "patient":
            if patient_id and patient_id != user_id:
                raise ValueError("create_thread: a thread can only have one patient")
            patient_id = user_id
        else:
            physician_ids.append(user_id)

    if not patient_id:
        raise ValueError("create_thread: a thread must include exactly one patient")

    return await _insert_thread(title, patient_id, physician_ids)


async def _insert_thread(
    title: str, patient_id: str, physician_ids: list[str]
) -> ApiThread:
    thread_id = str(uuid.uuid4())
    date_created = now_ms()
    # dict.fromkeys dedupes while preserving the caller's ordering.
    care_team = list(dict.fromkeys(physician_ids))

    async def write(q: Querier) -> None:
        await q(
            insert(threads).values(
                id=thread_id,
                title=title,
                patient_id=patient_id,
                date_created=date_created,
            )
        )
        if care_team:
            await q(
                pg_insert(threads_physicians)
                .values(
                    [
                        {"thread_id": thread_id, "physician_id": physician_id}
                        for physician_id in care_team
                    ]
                )
                .on_conflict_do_nothing()
            )

    await tx(write)

    thread = await get_thread_by_id(thread_id)
    if thread is None:
        raise RuntimeError(f"_insert_thread: insert vanished ({thread_id})")
    return thread


async def get_thread_metadata(thread_id: str) -> ThreadMetadata:
    row = await one(select(threads.c.metadata).where(threads.c.id == thread_id))
    if row is None:
        raise ValueError(f"get_thread_metadata: unknown thread {thread_id}")
    return normalize_metadata(row["metadata"])


async def set_thread_metadata(thread_id: str, metadata: ThreadMetadata) -> None:
    await query(
        update(threads)
        .where(threads.c.id == thread_id)
        .values(metadata=metadata.model_dump())
    )
