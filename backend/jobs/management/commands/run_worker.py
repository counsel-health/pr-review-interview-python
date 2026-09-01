"""
Run the background job worker.

Deliberately a separate process rather than something started from
``AppConfig.ready()``: under the dev server's autoreloader ``ready()`` runs in
both the reloader and the child process, which would give you two competing
workers.
"""

from typing import Any

from django.core.management.base import BaseCommand

from jobs.worker import Worker


class Command(BaseCommand):
    help = "Poll the jobs queue and run job handlers until interrupted."

    def handle(self, *args: Any, **options: Any) -> None:
        worker = Worker()
        worker.install_signal_handlers()
        worker.run()
