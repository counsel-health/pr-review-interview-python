"""
Delete the local embedded-PostgreSQL database entirely.

The next command that touches the database recreates the cluster; run
``manage.py migrate`` afterwards to rebuild the schema and reload the seed.
Refuses to run when ``DATABASE_URL`` points at an external server, since it
has no business deleting someone else's data directory.
"""

import os
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from counsel.db import data_dir, stop_embedded_server


class Command(BaseCommand):
    help = "Delete the local embedded PostgreSQL data directory."

    def handle(self, *args: Any, **options: Any) -> None:
        if os.environ.get("DATABASE_URL"):
            raise CommandError(
                "DATABASE_URL is set; refusing to reset an externally managed database"
            )

        directory = data_dir()
        if not directory.exists():
            self.stdout.write(f"{directory} did not exist; nothing to reset")
            return

        stop_embedded_server()
        self.stdout.write(self.style.SUCCESS(f"removed {directory}"))
