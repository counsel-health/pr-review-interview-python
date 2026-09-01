"""
Environment-derived settings.

Everything here has a working default so a fresh checkout runs with no `.env`
file at all; see `.env.example` at the repo root for the full list.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Name of the application database inside the PostgreSQL cluster.
DATABASE_NAME = "counsel"

#: Where the embedded PostgreSQL server keeps its data directory when
#: ``DATABASE_URL`` is not set. Mirrors ``PGLITE_DATA_DIR`` in the original
#: TypeScript app.
DEFAULT_DATA_DIR = ".pgdata"


def database_url() -> str | None:
    """An external PostgreSQL to use instead of the embedded server, if set."""
    return os.environ.get("DATABASE_URL") or None


def data_dir() -> Path:
    """Absolute path of the embedded server's data directory."""
    configured = os.environ.get("PGDATA_DIR", DEFAULT_DATA_DIR)
    return Path(configured).expanduser().resolve()


def run_worker_in_api_server() -> bool:
    """
    Whether the API server should run a job worker from its lifespan.

    On by default so a fresh checkout needs one process, not two. Set
    ``RUN_WORKER=0`` when running ``run-worker`` separately, or the two
    workers compete for the same jobs.
    """
    return os.environ.get("RUN_WORKER", "1") != "0"


def relay_webhook_secret() -> str | None:
    """Shared secret for signing and verifying Relay webhook payloads."""
    return os.environ.get("RELAY_WEBHOOK_SECRET") or None
