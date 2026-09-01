"""
Health check plus a lightweight smoke test of the domain layer. Verifies
FastAPI and PostgreSQL are wired together end-to-end without needing a browser.

- ``GET``  — read path (users + threads + a thread's messages).
- ``POST`` — write path (appends a patient-authored message to the first
  thread, exercising the message insert and the author CHECK constraint).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import ApiError
from app.api.http import json_response
from app.dto import HealthCounts, HealthResponse, HealthWriteResponse
from app.messages import append_message, list_thread_messages
from app.threads import list_threads
from app.users import list_all_users

router = APIRouter()

#: The seeded patient. The demo frontend hardcodes this id too.
DEFAULT_PATIENT_ID = "user1"


@router.get("/health", response_model=None)
async def get_health() -> JSONResponse:
    try:
        users = await list_all_users()
        threads = await list_threads()
        first_thread = threads[0] if threads else None
        first_messages = (
            await list_thread_messages(first_thread.id) if first_thread else []
        )
    except Exception as exc:
        raise ApiError("health_failed", str(exc), 500) from exc

    return json_response(
        HealthResponse(
            ok=True,
            counts=HealthCounts(
                users=len(users),
                threads=len(threads),
                messages_in_first_thread=len(first_messages),
            ),
            first_thread=first_thread,
            first_message=first_messages[0] if first_messages else None,
        )
    )


@router.post("/health", response_model=None)
async def post_health() -> JSONResponse:
    try:
        threads = await list_threads()
    except Exception as exc:
        raise ApiError("write_failed", str(exc), 500) from exc

    if not threads:
        raise ApiError("no_threads", "no threads to write to", 404)

    target = threads[0]
    patient_id = next(
        (user for user in target.users if user == DEFAULT_PATIENT_ID),
        DEFAULT_PATIENT_ID,
    )
    try:
        inserted = await append_message(
            thread_id=target.id,
            author_id=patient_id,
            author_role="patient",
            text=f"health POST @ {datetime.now(UTC).isoformat()}",
        )
    except Exception as exc:
        raise ApiError("write_failed", str(exc), 500) from exc

    return json_response(HealthWriteResponse(ok=True, inserted=inserted))
