"""
REST endpoints for threads.

- ``GET  /api/threads?query=...`` — list threads, optionally filtered.
- ``POST /api/threads``           — create a thread from a list of user ids.

Thin wrappers around the domain layer in ``app/``.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import ApiError
from app.api.http import json_response
from app.dto import CreateThreadRequest
from app.threads import create_thread, list_threads

router = APIRouter()


@router.get("/threads", response_model=None)
async def get_threads(query: str | None = None) -> JSONResponse:
    try:
        return json_response(await list_threads(query))
    except Exception as exc:
        raise ApiError("threads_failed", str(exc), 500) from exc


@router.post("/threads", status_code=201, response_model=None)
async def post_threads(body: CreateThreadRequest) -> JSONResponse:
    try:
        return json_response(await create_thread(body.title, body.userIds), 201)
    except Exception as exc:
        # Anything the domain layer rejects (an unknown user id, more than one
        # patient) is a bad request, not a server fault.
        raise ApiError("create_thread_failed", str(exc), 400) from exc
