"""
Job handler: refresh a thread's summary after new inbound activity.
"""

from __future__ import annotations

from typing import Any, TypedDict

from sqlalchemy import select, update

from app.ai.summarize import summarize
from app.db import query
from app.schema import messages, threads


class RefreshSummaryPayload(TypedDict):
    threadId: str


async def handle_refresh_summary(payload: Any) -> None:
    thread_id = str(payload["threadId"])

    # Pull the thread's entire message history and regenerate the summary from
    # scratch every time.
    result = await query(
        select(messages.c.message)
        .where(messages.c.thread_id == thread_id)
        .order_by(messages.c.msg_index)
    )
    summary = summarize(row["message"] for row in result.rows)

    await query(
        update(threads).where(threads.c.id == thread_id).values(summary=summary)
    )
