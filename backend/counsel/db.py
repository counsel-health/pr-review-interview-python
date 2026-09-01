"""
Local PostgreSQL provisioning.

The app targets a real PostgreSQL server. To keep a fresh checkout runnable
with nothing but `uv sync`, the default backing store is an *embedded*
PostgreSQL: `pgembed` ships the server binaries as a wheel and runs a
postmaster out of a gitignored data directory (``PGDATA_DIR``, default
``.pgdata``) listening on a unix socket inside it.

The postmaster is deliberately left running between processes
(``cleanup_mode=None``) because more than one process talks to it — the
Django dev server and ``manage.py run_worker`` at minimum. ``manage.py
db_reset`` is what tears it down.

Set ``DATABASE_URL`` to point at any other PostgreSQL instance instead; the
embedded server is then never started.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, TypedDict
from urllib.parse import unquote, urlparse

DEFAULT_DATA_DIR = ".pgdata"
DATABASE_NAME = "counsel"


class DatabaseConfig(TypedDict):
    """The subset of Django's DATABASES entry this module produces."""

    ENGINE: str
    NAME: str
    USER: str
    PASSWORD: str
    HOST: str
    PORT: str


def data_dir() -> Path:
    """Absolute path of the embedded server's data directory."""
    configured = os.environ.get("PGDATA_DIR", DEFAULT_DATA_DIR)
    return Path(configured).expanduser().resolve()


def _parse_database_url(url: str) -> DatabaseConfig:
    parsed = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")) or DATABASE_NAME,
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": unquote(parsed.hostname or ""),
        "PORT": str(parsed.port or ""),
    }


def start_embedded_server() -> Any:
    """
    Start (or attach to an already-running) embedded PostgreSQL server and
    make sure the application database exists.

    Returns the pgembed server handle. Attaching to a live postmaster is
    cheap, so this is safe to call on every management command.
    """
    import psycopg
    from pgembed import get_server

    # pgembed narrates its handle bookkeeping at INFO on every process exit,
    # which is noise in front of ordinary manage.py output.
    logging.getLogger("pgembed").setLevel(logging.WARNING)

    server = get_server(data_dir(), cleanup_mode=None)

    # pgembed only guarantees the `postgres` maintenance database. Create the
    # application database on first boot; CREATE DATABASE cannot run inside a
    # transaction, hence autocommit.
    with psycopg.connect(server.get_uri(), autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (DATABASE_NAME,)
        ).fetchone()
        if exists is None:
            conn.execute(f'CREATE DATABASE "{DATABASE_NAME}"')

    return server


def stop_embedded_server() -> None:
    """Stop the embedded postmaster and delete its data directory."""
    import shutil

    from django.db import connections
    from pgembed import get_server, pg_ctl

    directory = data_dir()
    if not directory.exists():
        return

    connections.close_all()

    # pgembed's get_server() hands back a cached handle for a pgdata directory
    # and ignores the cleanup_mode of later callers, so asking it to clean up
    # would be a no-op here: loading settings already attached a handle with
    # cleanup_mode=None. Stop the postmaster directly instead.
    server = get_server(directory, cleanup_mode=None)
    if server.get_pid() is not None:
        pg_ctl(["-w", "stop"], pgdata=directory)
    shutil.rmtree(directory)


def database_config() -> DatabaseConfig:
    """Build the Django DATABASES['default'] entry."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return _parse_database_url(url)

    server = start_embedded_server()
    uri = urlparse(server.get_uri(database=DATABASE_NAME))
    # The embedded server listens on a unix socket; psycopg (and therefore
    # Django) takes the socket *directory* as the host.
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DATABASE_NAME,
        "USER": unquote(uri.username or "postgres"),
        "PASSWORD": unquote(uri.password or ""),
        "HOST": str(data_dir()),
        "PORT": "",
    }
