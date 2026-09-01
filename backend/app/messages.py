"""
Message domain layer.

Every write path into ``messages`` goes through :func:`append_message`, and
every read path renders rows through :func:`to_api`. Keeping both in one place
is what guarantees the ``author_patient_id`` / ``author_physician_id`` split is
written consistently and that the UI always sees the same ``ApiMessage`` shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import func, insert, select

from app.clock import now_ms
from app.db import one, query
from app.dto import ApiMessage, UserRole
from app.schema import messages
from app.threads import record_message_for_metadata
from app.users import resolve_role

MESSAGE_COLUMNS = (
    messages.c.id,
    messages.c.thread_id,
    messages.c.author_patient_id,
    messages.c.author_physician_id,
    messages.c.message,
    messages.c.timestamp,
    messages.c.msg_index,
)

SELECT_MESSAGE = select(*MESSAGE_COLUMNS)


def to_api(row: Mapping[str, Any]) -> ApiMessage:
    """
    Map a message row to its DTO.

    The two nullable author columns collapse into the single ``userId`` the UI
    works with; the ``messages_author_xor`` CHECK constraint guarantees exactly
    one of them is set, so the fallback below can never yield None.
    """
    author_id = row["author_patient_id"] or row["author_physician_id"]
    if author_id is None:
        raise ValueError(f"message {row['id']} has no author")
    return ApiMessage(
        id=row["id"],
        userId=author_id,
        threadId=row["thread_id"],
        message=row["message"],
        timestamp=row["timestamp"],
        msgIndex=row["msg_index"],
    )


async def list_thread_messages(thread_id: str) -> list[ApiMessage]:
    """Every message in a thread, in conversation order."""
    result = await query(
        SELECT_MESSAGE.where(messages.c.thread_id == thread_id).order_by(
            messages.c.msg_index
        )
    )
    return [to_api(row) for row in result.rows]


async def get_next_msg_index(thread_id: str) -> int:
    """The msg_index a new message in this thread should take."""
    row = await one(
        select(
            (func.coalesce(func.max(messages.c.msg_index), -1) + 1).label("next")
        ).where(messages.c.thread_id == thread_id)
    )
    return int(row["next"]) if row else 0


async def append_message(
    thread_id: str,
    author_id: str,
    author_role: UserRole,
    text: str,
) -> ApiMessage:
    """
    Append a message to a thread. The author column written depends on the
    author's role.

    The index is read and then written non-atomically, which two concurrent
    appends to the same thread can race. That race is safe rather than
    corrupting because ``UNIQUE(thread_id, msg_index)`` is enforced in the
    schema: the loser's INSERT fails outright instead of silently producing a
    duplicate index. Callers surface the error; they must not paper over it.
    """
    next_index = await get_next_msg_index(thread_id)

    row = await one(
        insert(messages)
        .values(
            thread_id=thread_id,
            author_patient_id=author_id if author_role == "patient" else None,
            author_physician_id=author_id if author_role == "physician" else None,
            message=text,
            timestamp=now_ms(),
            msg_index=next_index,
        )
        .returning(*MESSAGE_COLUMNS)
    )
    if row is None:
        raise RuntimeError("append_message: insert returned no row")
    return to_api(row)


async def send_message(thread_id: str, user_id: str, text: str) -> ApiMessage:
    """
    Send a message to a thread on behalf of a user.

    Resolves the author's role (patient vs physician) before delegating to
    :func:`append_message`. This is the orchestration the UI calls into via the
    REST layer.

    Not to be confused with ``app.jobs.queue.send_message``, which enqueues a
    background job. This one is a chat message.
    """
    role = await resolve_role(user_id)
    message = await append_message(
        thread_id=thread_id,
        author_id=user_id,
        author_role=role,
        text=text,
    )
    # Patient messages bump the unresponded counter; a physician reply clears it.
    await record_message_for_metadata(thread_id, role)
    return message
