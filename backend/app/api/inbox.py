"""
Read endpoint for the upcoming mobile client.

- ``GET /api/inbox?physicianId=...`` — the threads on a care team member's
  plate, each with its messages, so the app can render an inbox in one call.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.errors import ApiError
from app.api.http import json_response
from app.db import query
from app.schema import messages, threads, threads_physicians

router = APIRouter()


@router.get("/inbox", response_model=None)
async def get_inbox(
    # Whose inbox to load — the mobile client tells us which physician.
    physician_id: str | None = Query(default=None, alias="physicianId"),
) -> JSONResponse:
    if not physician_id:
        raise ApiError("invalid_request", "physicianId is required", 400)

    try:
        # Every thread this physician is on.
        thread_rows = await query(
            select(
                threads.c.id,
                threads.c.title,
                threads.c.patient_id,
                threads.c.metadata,
            )
            .select_from(
                threads.join(
                    threads_physicians,
                    threads_physicians.c.thread_id == threads.c.id,
                )
            )
            .where(threads_physicians.c.physician_id == physician_id)
            .order_by(threads.c.date_created.desc())
        )

        inbox: list[dict[str, Any]] = []
        for thread in thread_rows.rows:
            # Load every message in this thread.
            message_rows = await query(
                select(
                    messages.c.id,
                    messages.c.thread_id,
                    messages.c.author_patient_id,
                    messages.c.author_physician_id,
                    messages.c.message,
                    messages.c.timestamp,
                    messages.c.msg_index,
                )
                .where(messages.c.thread_id == thread["id"])
                .order_by(messages.c.timestamp.desc())
            )
            inbox.append({**thread, "messages": message_rows.rows})
    except Exception as exc:
        raise ApiError("inbox_failed", str(exc), 500) from exc

    return json_response(inbox)
