"""
Job worker. Simulates an SQS consumer without the infrastructure: it polls the
queue (``app/jobs/queue.py``), dispatches each job to a handler by name, and
acks/nacks via the SQS-shaped verbs:

    receive_messages -> claim a batch (with a visibility timeout)
    delete_message   -> ack on success
    release_message  -> nack on failure (the job becomes visible again until
                        max_attempts, after which it lands in 'failed')

Handlers must be idempotent, because delivery is at-least-once.

There are two ways to run it:

* The API server starts one from its lifespan (``app/main.py``), so a job
  enqueued by a request is picked up while the server is running.
* ``uv run run-worker`` runs one in its own process, which is what a
  deployment would do. Set ``RUN_WORKER=0`` on the API server in that case so
  the two do not compete for the same jobs.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from collections.abc import Awaitable, Callable
from typing import Any

from app.db import dispose_engine
from app.jobs.handlers.notify_care_team import handle_notify_care_team
from app.jobs.handlers.refresh_summary import handle_refresh_summary
from app.jobs.handlers.summarize_thread import handle_summarize_thread
from app.jobs.queue import (
    ReceivedJob,
    delete_message,
    receive_messages,
    release_message,
)

logger = logging.getLogger(__name__)

JobHandler = Callable[[Any], Awaitable[None]]

#: Maps a job ``name`` (as passed to app.jobs.queue.send_message) to its
#: handler. Add new job types here.
HANDLERS: dict[str, JobHandler] = {
    "summarize_thread": handle_summarize_thread,
    "refresh_summary": handle_refresh_summary,
    "notify_care_team": handle_notify_care_team,
}

BATCH_SIZE = 5
VISIBILITY_TIMEOUT_MS = 30_000
IDLE_DELAY_SECONDS = 1.0
ERROR_DELAY_SECONDS = 3.0


class Worker:
    """A single-task polling consumer. Runs until :meth:`stop` is called."""

    def __init__(self, handlers: dict[str, JobHandler] | None = None) -> None:
        self.handlers = HANDLERS if handlers is None else handlers
        self._stopping = asyncio.Event()

    def stop(self) -> None:
        self._stopping.set()

    async def process_job(self, job: ReceivedJob) -> None:
        handler = self.handlers.get(job.name)
        if handler is None:
            await release_message(job.receipt_handle, f'no handler for job "{job.name}"')
            return

        try:
            await handler(job.payload)
        except Exception as exc:
            logger.exception("[worker] job %s (%s) failed", job.id, job.name)
            await release_message(job.receipt_handle, str(exc))
        else:
            await delete_message(job.receipt_handle)

    async def run(self) -> None:
        logger.info("[worker] started; polling for jobs")
        while not self._stopping.is_set():
            try:
                claimed = await receive_messages(
                    max_messages=BATCH_SIZE,
                    visibility_timeout_ms=VISIBILITY_TIMEOUT_MS,
                )
            except Exception:
                logger.exception("[worker] poll error")
                await self._pause(ERROR_DELAY_SECONDS)
                continue

            for job in claimed:
                if self._stopping.is_set():
                    break
                await self.process_job(job)

            # Drain greedily: only idle when the queue came back empty.
            if not claimed:
                await self._pause(IDLE_DELAY_SECONDS)

        logger.info("[worker] stopped")

    async def _pause(self, seconds: float) -> None:
        """Sleep, but wake immediately if a stop is requested."""
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._stopping.wait(), timeout=seconds)


async def run_forever() -> None:
    """Run a worker until SIGTERM or SIGINT arrives."""
    worker = Worker()

    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, worker.stop)

    try:
        await worker.run()
    finally:
        await dispose_engine()


def main() -> None:
    """Standalone entrypoint: ``uv run run-worker``."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
