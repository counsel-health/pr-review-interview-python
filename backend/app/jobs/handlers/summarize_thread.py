"""
Job handler: produce a fresh summary for a thread and write it to
``threads.summary``.

Idempotent by construction — it recomputes the summary from the thread's full
message history, so a redelivery just writes the same text again.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.ai.summarize import summarize
from app.clock import now_ms
from app.db import query
from app.schema import messages

# Write the summary and bump the metadata timestamp in the same UPDATE.
# jsonb_set rewrites one key and leaves the rest of the blob untouched, so a
# concurrent writer's change to another key is not clobbered — which a
# read-modify-write of the whole blob would do.
UPDATE_SUMMARY = """
UPDATE threads
SET summary = :summary,
    metadata = jsonb_set(
      metadata,
      '{lastSummaryGenerated}',
      to_jsonb(CAST(:generated_at AS BIGINT)),
      true
    )
WHERE id = :thread_id
"""


async def handle_summarize_thread(payload: Any) -> None:
    thread_id = str(payload["threadId"])

    result = await query(
        select(messages.c.message)
        .where(messages.c.thread_id == thread_id)
        .order_by(messages.c.msg_index)
    )
    summary = summarize(row["message"] for row in result.rows)

    await query(
        UPDATE_SUMMARY,
        {"summary": summary, "generated_at": now_ms(), "thread_id": thread_id},
    )
