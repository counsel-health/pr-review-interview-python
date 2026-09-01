"""
Job handler: refresh a thread's summary after new inbound activity.
"""

from __future__ import annotations

from typing import Any, TypedDict

from core.ai.summarize import summarize
from core.models import Message, Thread


class RefreshSummaryPayload(TypedDict):
    threadId: str


def handle_refresh_summary(payload: Any) -> None:
    thread_id = payload["threadId"]

    # Pull the thread's entire message history and regenerate the summary from
    # scratch every time.
    bodies = list(
        Message.objects.filter(thread_id=thread_id)
        .order_by("msg_index")
        .values_list("message", flat=True)
    )

    Thread.objects.filter(id=thread_id).update(summary=summarize(bodies))
