"""
One-off backfill: generate a summary for every thread that doesn't have one
yet, so threads seeded before the summarizer existed get one too.

Run it with ``uv run backfill-summaries``.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select, update

from app.ai.summarize import summarize
from app.db import dispose_engine, query
from app.schema import messages, threads


async def summarize_one(thread_id: str) -> None:
    result = await query(
        select(messages.c.message)
        .where(messages.c.thread_id == thread_id)
        .order_by(messages.c.msg_index)
    )
    summary = summarize(row["message"] for row in result.rows)

    await query(
        update(threads).where(threads.c.id == thread_id).values(summary=summary)
    )


async def run() -> None:
    pending = await query(select(threads.c.id).where(threads.c.summary.is_(None)))
    thread_ids = [str(row["id"]) for row in pending.rows]

    # Summarize every thread at once so the backfill finishes fast.
    await asyncio.gather(*[summarize_one(thread_id) for thread_id in thread_ids])

    print(f"backfilled {len(thread_ids)} threads")


async def _main() -> None:
    try:
        await run()
    finally:
        await dispose_engine()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
