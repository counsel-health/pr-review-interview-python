"""
Job handler: produce a fresh summary for a thread and write it to
``threads.summary``.

Idempotent by construction — it recomputes the summary from the thread's full
message history, so a redelivery just writes the same (or a newer) value.
"""

from __future__ import annotations

from typing import Any, TypedDict

from django.db.models.expressions import RawSQL

from core.ai.summarize import summarize
from core.clock import now_ms
from core.models import Message, Thread


class SummarizeThreadPayload(TypedDict):
    threadId: str


def handle_summarize_thread(payload: Any) -> None:
    thread_id = payload["threadId"]

    bodies = list(
        Message.objects.filter(thread_id=thread_id)
        .order_by("msg_index")
        .values_list("message", flat=True)
    )
    summary = summarize(bodies)

    # Write the summary and bump the metadata timestamp in the same UPDATE.
    # jsonb_set edits the one key server-side, so a concurrent write to
    # another metadata key (the unresponded counter, say) isn't clobbered the
    # way a read-modify-write of the whole blob would clobber it.
    Thread.objects.filter(id=thread_id).update(
        summary=summary,
        metadata=RawSQL(
            "jsonb_set(metadata, '{lastSummaryGenerated}', to_jsonb(%s::bigint), true)",
            (now_ms(),),
        ),
    )
