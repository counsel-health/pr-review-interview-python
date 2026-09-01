"""
Job worker. Simulates an SQS consumer without the infrastructure: it polls the
queue (``jobs/queue.py``), dispatches each job to a handler by name, and
acks/nacks via the SQS-shaped verbs:

    receive_messages -> claim a batch (with a visibility timeout)
    delete_message   -> ack on success
    release_message  -> nack on failure (the job becomes visible again until
                        max_attempts, after which it lands in 'failed')

Run it with ``manage.py run_worker``. Handlers must be idempotent, because
delivery is at-least-once.
"""

from __future__ import annotations

import logging
import signal
import time
from types import FrameType
from typing import Any, Callable

from jobs.handlers.notify_care_team import handle_notify_care_team
from jobs.handlers.refresh_summary import handle_refresh_summary
from jobs.handlers.summarize_thread import handle_summarize_thread
from jobs.queue import ReceivedJob, delete_message, receive_messages, release_message

logger = logging.getLogger(__name__)

JobHandler = Callable[[Any], None]

#: Maps a job ``name`` (as passed to jobs.queue.send_message) to its handler.
#: Add new job types here.
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
    """A single-threaded polling consumer. Stops on SIGTERM/SIGINT."""

    def __init__(self, handlers: dict[str, JobHandler] | None = None) -> None:
        self.handlers = HANDLERS if handlers is None else handlers
        self._stopping = False

    def stop(self) -> None:
        self._stopping = True

    def install_signal_handlers(self) -> None:
        def shutdown(signum: int, frame: FrameType | None) -> None:
            logger.info("[worker] shutdown requested (%s)", signal.Signals(signum).name)
            self.stop()

        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)

    def process_job(self, job: ReceivedJob) -> None:
        handler = self.handlers.get(job.name)
        if handler is None:
            release_message(job.receipt_handle, f'no handler for job "{job.name}"')
            return

        try:
            handler(job.payload)
        except Exception as exc:
            logger.exception("[worker] job %s (%s) failed", job.id, job.name)
            release_message(job.receipt_handle, str(exc))
        else:
            delete_message(job.receipt_handle)

    def run(self) -> None:
        logger.info("[worker] started; polling for jobs")
        while not self._stopping:
            try:
                jobs = receive_messages(
                    max_messages=BATCH_SIZE,
                    visibility_timeout_ms=VISIBILITY_TIMEOUT_MS,
                )
            except Exception:
                logger.exception("[worker] poll error")
                time.sleep(ERROR_DELAY_SECONDS)
                continue

            for job in jobs:
                if self._stopping:
                    break
                self.process_job(job)

            # Drain greedily: only idle when the queue came back empty.
            if not jobs:
                time.sleep(IDLE_DELAY_SECONDS)

        logger.info("[worker] stopped")
