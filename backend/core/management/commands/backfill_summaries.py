"""
One-off backfill: generate a summary for every thread that doesn't have one
yet, so threads seeded before the summarizer existed get one too.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.core.management.base import BaseCommand

from core.ai.summarize import summarize
from core.models import Message, Thread


def summarize_one(thread_id: str) -> None:
    bodies = list(
        Message.objects.filter(thread_id=thread_id)
        .order_by("msg_index")
        .values_list("message", flat=True)
    )
    Thread.objects.filter(id=thread_id).update(summary=summarize(bodies))


class Command(BaseCommand):
    help = "Generate a summary for every thread that doesn't have one yet."

    def handle(self, *args: Any, **options: Any) -> None:
        thread_ids = list(
            Thread.objects.filter(summary__isnull=True).values_list("id", flat=True)
        )

        # Summarize every thread at once so the backfill finishes fast.
        with ThreadPoolExecutor(max_workers=len(thread_ids) or 1) as pool:
            list(pool.map(summarize_one, thread_ids))

        self.stdout.write(self.style.SUCCESS(f"backfilled {len(thread_ids)} threads"))
