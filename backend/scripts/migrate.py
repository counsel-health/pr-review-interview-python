"""
Apply pending migrations, in order, up to the newest revision.

Safe to re-run: Alembic skips revisions already recorded in
``alembic_version``. On a fresh checkout this also initializes the embedded
PostgreSQL cluster and creates the application database, because
``migrations/env.py`` resolves its URL through ``app/db.py``.

Run it with ``uv run migrate``.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    print("migrations complete.")


if __name__ == "__main__":
    main()
