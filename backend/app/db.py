"""
Database access, plus the lifecycle of the local PostgreSQL server.

Two things live here.

**The query helpers.** :func:`query`, :func:`one`, :func:`exec_sql` and
:func:`tx` are the whole data-access vocabulary; there is no ORM, no session
and no unit of work. Each helper takes either a SQLAlchemy Core statement
built against the tables in ``app/schema.py`` or a raw SQL string, and hands
back plain dicts. Rows become DTOs in the domain layer, never here.

**The server.** The app targets a real PostgreSQL. To keep a fresh checkout
runnable with nothing but `uv sync`, the default backing store is an
*embedded* PostgreSQL: `pgembed` ships the server binaries as a wheel and runs
a postmaster out of a gitignored data directory (``PGDATA_DIR``, default
``.pgdata``) listening on a unix socket inside it.

The postmaster is deliberately left running between processes
(``cleanup_mode=None``) because more than one process talks to it — the API
server and a standalone worker at minimum. ``db-reset`` is what tears it down.

Set ``DATABASE_URL`` to point at any other PostgreSQL instance instead; the
embedded server is then never started.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import Executable, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.config import DATABASE_NAME, data_dir, database_url

#: What the helpers accept: a Core statement, or raw SQL with ``:name`` binds.
Statement = str | Executable

#: Bound parameters for a statement, keyed by name.
Params = Mapping[str, Any]


@dataclass(frozen=True)
class QueryResult:
    """Rows from a statement, as plain dicts. Empty for statements that
    return none."""

    rows: list[dict[str, Any]]


class Querier(Protocol):
    """The callable :func:`tx` hands to its body — :func:`query`, rebound to
    the transaction."""

    async def __call__(
        self, statement: Statement, params: Params | None = None
    ) -> QueryResult: ...


async def query(statement: Statement, params: Params | None = None) -> QueryResult:
    """Run a statement on its own connection and collect the rows."""
    engine = await get_engine()
    async with engine.begin() as connection:
        return await _run(connection, statement, params)


async def one(statement: Statement, params: Params | None = None) -> dict[str, Any] | None:
    """The first row a statement returns, or None if it returned none."""
    result = await query(statement, params)
    return result.rows[0] if result.rows else None


async def exec_sql(sql: str) -> None:
    """Run a raw SQL script for its side effects. May contain several
    statements."""
    engine = await get_engine()
    async with engine.begin() as connection:
        await connection.exec_driver_sql(sql)


async def tx[T](body: Callable[[Querier], Awaitable[T]]) -> T:
    """
    Run ``body`` inside a single transaction.

    ``body`` receives a :class:`Querier` with the same signature as
    :func:`query`; every statement it runs shares one connection and commits or
    rolls back together.
    """
    engine = await get_engine()
    async with engine.begin() as connection:

        async def scoped(
            statement: Statement, params: Params | None = None
        ) -> QueryResult:
            return await _run(connection, statement, params)

        return await body(scoped)


async def _run(
    connection: AsyncConnection, statement: Statement, params: Params | None
) -> QueryResult:
    compiled = text(statement) if isinstance(statement, str) else statement
    result = await connection.execute(compiled, dict(params) if params else None)
    if not result.returns_rows:
        return QueryResult(rows=[])
    return QueryResult(rows=[dict(row._mapping) for row in result])


_engine: AsyncEngine | None = None
_engine_lock = asyncio.Lock()


async def get_engine() -> AsyncEngine:
    """The process-wide async engine, created on first use."""
    global _engine
    if _engine is not None:
        return _engine
    async with _engine_lock:
        if _engine is None:
            # Starting the embedded postmaster blocks; keep it off the loop.
            url = await asyncio.to_thread(resolve_database_url)
            _engine = create_async_engine(url, pool_pre_ping=True)
    return _engine


async def dispose_engine() -> None:
    """Close every pooled connection. Called on API server shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


def resolve_database_url() -> str:
    """
    The URL the engine should connect to, starting the embedded server if
    that is where the data lives.
    """
    configured = database_url()
    if configured:
        return _with_async_driver(configured)
    server = start_embedded_server()
    return _with_async_driver(server.get_uri(database=DATABASE_NAME))


def _with_async_driver(url: str) -> str:
    """Force the async psycopg driver regardless of how the URL was spelled."""
    return make_url(url).set(drivername="postgresql+psycopg").render_as_string(
        hide_password=False
    )


def start_embedded_server() -> Any:
    """
    Start (or attach to an already-running) embedded PostgreSQL server and
    make sure the application database exists.

    Returns the pgembed server handle. Attaching to a live postmaster is
    cheap, so this is safe to call on every entrypoint.
    """
    import psycopg
    from pgembed import get_server

    # pgembed narrates its handle bookkeeping at INFO on every process exit,
    # which is noise in front of ordinary server output.
    logging.getLogger("pgembed").setLevel(logging.WARNING)

    server = get_server(data_dir(), cleanup_mode=None)

    # pgembed only guarantees the `postgres` maintenance database. Create the
    # application database on first boot; CREATE DATABASE cannot run inside a
    # transaction, hence autocommit.
    with psycopg.connect(server.get_uri(), autocommit=True) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (DATABASE_NAME,)
        ).fetchone()
        if exists is None:
            connection.execute(f'CREATE DATABASE "{DATABASE_NAME}"')

    return server


def stop_embedded_server() -> None:
    """Stop the embedded postmaster and delete its data directory."""
    from pgembed import get_server, pg_ctl

    directory = data_dir()
    if not directory.exists():
        return

    # pgembed's get_server() hands back a cached handle for a pgdata directory
    # and ignores the cleanup_mode of later callers, so asking it to clean up
    # would be a no-op here: an earlier caller in this process may already have
    # attached a handle with cleanup_mode=None. Stop the postmaster directly
    # instead.
    server = get_server(directory, cleanup_mode=None)
    if server.get_pid() is not None:
        pg_ctl(["-w", "stop"], pgdata=directory)
    shutil.rmtree(directory)
