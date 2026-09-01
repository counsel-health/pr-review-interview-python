"""
End-to-end smoke test of the domain layer and the job queue, without a browser
or an HTTP server. Exercises the read paths, both message write paths, thread
creation, search, and one full enqueue/receive/handle/ack cycle.

Writes real rows into the local database — run it against the dev database
only.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from core.messages import append_message, list_thread_messages
from core.models import Thread
from core.threads import create_thread, get_thread_by_id, list_threads
from core.users import list_all_users
from jobs.handlers.summarize_thread import handle_summarize_thread
from jobs.queue import delete_message, receive_messages
from jobs.queue import send_message as enqueue_job


class Command(BaseCommand):
    help = "Exercise the domain layer and job queue end to end."

    def handle(self, *args: Any, **options: Any) -> None:
        out = self.stdout

        users = list_all_users()
        out.write(f"USERS: {users}")

        threads = list_threads()
        if not threads:
            raise CommandError("no threads in the database; run `manage.py migrate` first")
        out.write(f"threads sample (first 2): {threads[:2]}")

        target_id = threads[0]["id"]
        messages = list_thread_messages(target_id)
        out.write(
            f"msg count thread[0]: {len(messages)} "
            f"first: {messages[0] if messages else None} "
            f"last: {messages[-1] if messages else None}"
        )

        patient_message = append_message(
            thread_id=target_id,
            author_id="user1",
            author_role="patient",
            text="sanity: patient",
        )
        out.write(f"append_message patient -> {patient_message}")

        physician_message = append_message(
            thread_id=target_id,
            author_id="user2",
            author_role="physician",
            text="sanity: physician",
        )
        out.write(f"append_message physician -> {physician_message}")

        created = create_thread("Sanity new thread", ["user1", "user2", "user3"])
        out.write(f"create_thread -> {created}")

        refetched = get_thread_by_id(created["id"])
        out.write(f"refetched -> {refetched}")
        if refetched != created:
            raise CommandError("get_thread_by_id disagreed with create_thread")

        searched = list_threads("sanity")
        out.write(f"search 'sanity' count: {len(searched)}")

        # Queue + summarize handler smoke test. The second enqueue carries the
        # same deduplication id, so it must not create a second job.
        dedup_id = f"summarize:{target_id}"
        first = enqueue_job(
            "summarize_thread", {"threadId": target_id}, deduplication_id=dedup_id
        )
        out.write(f"enqueue -> {first}")
        second = enqueue_job(
            "summarize_thread", {"threadId": target_id}, deduplication_id=dedup_id
        )
        out.write(f"enqueue (dup) -> {second}")
        if second != {"duplicate": True}:
            raise CommandError(f"expected the second enqueue to dedupe, got {second}")

        received = receive_messages(max_messages=5)
        out.write(f"received jobs: {len(received)}")
        if not received:
            raise CommandError("expected at least one job to be receivable")
        for job in received:
            handle_summarize_thread(job.payload)
            delete_message(job.receipt_handle)

        summary = Thread.objects.values_list("summary", flat=True).get(id=target_id)
        out.write(f"thread summary after job: {(summary or '')[:120]}")
        if not summary:
            raise CommandError("summarize_thread did not write a summary")

        out.write(self.style.SUCCESS("sanity test passed"))
