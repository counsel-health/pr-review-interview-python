"""
REST endpoints for the messages belonging to a thread.

- ``GET  /api/threads/{thread_id}/messages`` — list messages in order.
- ``POST /api/threads/{thread_id}/messages`` — append a message from a user.

The POST returns the inserted message as a bare ``ApiMessage`` object, not
wrapped in an envelope: the frontend client assigns the response straight into
its message list.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import ApiError
from app.api.http import json_response
from app.dto import SendMessageRequest
from app.messages import list_thread_messages, send_message

router = APIRouter()


@router.get("/threads/{thread_id}/messages", response_model=None)
async def get_thread_messages(thread_id: str) -> JSONResponse:
    try:
        return json_response(await list_thread_messages(thread_id))
    except Exception as exc:
        raise ApiError("messages_failed", str(exc), 500) from exc


@router.post("/threads/{thread_id}/messages", status_code=201, response_model=None)
async def post_thread_message(
    thread_id: str, body: SendMessageRequest
) -> JSONResponse:
    try:
        return json_response(
            await send_message(thread_id, body.userId, body.message), 201
        )
    except Exception as exc:
        raise ApiError("send_message_failed", str(exc), 400) from exc
