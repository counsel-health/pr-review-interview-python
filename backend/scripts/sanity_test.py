"""
Exercise the domain layer and the job queue end to end, without a browser.

Reads the seeded data, writes a message as each kind of author, creates and
re-fetches a thread, searches, then runs a job through the queue's full
enqueue / dedupe / receive / handle / ack cycle.

Run it with ``uv run sanity-test``.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db import dispose_engine, one
from app.jobs.handlers.summarize_thread import handle_summarize_thread
from app.jobs.queue import delete_message, receive_messages
from app.jobs.queue import send_message as enqueue_job
from app.messages import append_message, list_thread_messages
from app.schema import threads as threads_table
from app.threads import create_thread, get_thread_by_id, list_threads
from app.users import list_all_users


class SanityError(Exception):
    """A check the sanity test expected to hold did not."""


async def run() -> None:
    users = await list_all_users()
    print(f"USERS: {users}")

    threads = await list_threads()
    print(f"threads sample (first 2): {threads[:2]}")
    if not threads:
        raise SanityError("no threads; has `uv run migrate` been run?")

    target_id = threads[0].id
    messages = await list_thread_messages(target_id)
    print(
        f"msg count thread[0]: {len(messages)} "
        f"first: {messages[0] if messages else None} "
        f"last: {messages[-1] if messages else None}"
    )

    patient_message = await append_message(
        thread_id=target_id,
        author_id="user1",
        author_role="patient",
        text="sanity: patient",
    )
    print(f"append_message patient -> {patient_message}")

    physician_message = await append_message(
        thread_id=target_id,
        author_id="user2",
        author_role="physician",
        text="sanity: physician",
    )
    print(f"append_message physician -> {physician_message}")

    created = await create_thread("Sanity new thread", ["user1", "user2", "user3"])
    print(f"create_thread -> {created}")

    refetched = await get_thread_by_id(created.id)
    print(f"refetched -> {refetched}")
    if refetched != created:
        raise SanityError("get_thread_by_id disagreed with create_thread")

    searched = await list_threads("sanity")
    print(f"search 'sanity' count: {len(searched)}")
    if not searched:
        raise SanityError("search found nothing it just wrote")

    # Queue + summarize handler smoke test. The second enqueue carries the same
    # deduplication id, so it must not create a second job.
    dedup_id = f"summarize:{target_id}"
    first = await enqueue_job(
        "summarize_thread", {"threadId": target_id}, deduplication_id=dedup_id
    )
    print(f"enqueue -> {first}")
    second = await enqueue_job(
        "summarize_thread", {"threadId": target_id}, deduplication_id=dedup_id
    )
    print(f"enqueue (dup) -> {second}")
    if second != {"duplicate": True}:
        raise SanityError(f"expected the second enqueue to dedupe, got {second}")

    received = await receive_messages(max_messages=5)
    print(f"received jobs: {len(received)}")
    if not received:
        raise SanityError("expected at least one job to be receivable")
    for job in received:
        await handle_summarize_thread(job.payload)
        await delete_message(job.receipt_handle)

    row = await one(
        select(threads_table.c.summary).where(threads_table.c.id == target_id)
    )
    summary = row["summary"] if row else None
    print(f"thread summary after job: {(summary or '')[:120]}")
    if not summary:
        raise SanityError("summarize_thread did not write a summary")

    print("sanity test passed")


async def _main() -> None:
    try:
        await run()
    finally:
        await dispose_engine()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
