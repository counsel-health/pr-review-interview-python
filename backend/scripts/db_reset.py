"""
Reset the local database by stopping the embedded PostgreSQL server and
deleting its data directory. Follow it with ``uv run migrate`` to rebuild from
scratch.

Run it with ``uv run db-reset``.
"""

from __future__ import annotations

import sys

from app.config import data_dir, database_url
from app.db import stop_embedded_server


def main() -> None:
    if database_url():
        sys.exit(
            "DATABASE_URL is set, so this database is not ours to delete. "
            "Unset it to reset the embedded server instead."
        )

    directory = data_dir()
    if not directory.exists():
        print(f"{directory} did not exist; nothing to reset")
        return

    stop_embedded_server()
    print(f"removed {directory}")


if __name__ == "__main__":
    main()
