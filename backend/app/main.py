"""
The FastAPI application.

Run it with::

    uv run uvicorn app.main:app --port 8000

The REST API lives under ``/api``; the Next.js frontend proxies to it (see
``frontend/next.config.mjs``) so the browser only ever calls relative URLs.

**There is no authentication anywhere in this app.** The acting user is chosen
client-side and sent as ``userId`` in the request body, and the server trusts
it. There is no login, no session, no CSRF token, and no authorization check on
any endpoint. That is deliberate for this demo, not an oversight.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health, inbox, messages, threads, users, webhooks
from app.api.errors import install_error_handlers
from app.config import run_worker_in_api_server
from app.db import dispose_engine
from app.jobs.worker import Worker

logger = logging.getLogger(__name__)

# uvicorn only configures its own loggers, leaving the root one without a
# handler — which would silently drop everything the worker and the domain
# layer log. This is the process entrypoint, so it is the right place to set
# that up; basicConfig is a no-op if a handler is already installed.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Own the process-wide resources: the job worker and the database engine.

    The worker runs as a task alongside the server so a job enqueued by a
    request gets picked up without a second process. ``RUN_WORKER=0`` turns it
    off for deployments that run ``run-worker`` on its own.
    """
    worker: Worker | None = None
    worker_task: asyncio.Task[None] | None = None

    if run_worker_in_api_server():
        worker = Worker()
        worker_task = asyncio.create_task(worker.run())

    try:
        yield
    finally:
        if worker is not None and worker_task is not None:
            worker.stop()
            await worker_task
        await dispose_engine()


app = FastAPI(title="Counsel API", lifespan=lifespan)

install_error_handlers(app)

app.include_router(users.router, prefix="/api")
app.include_router(threads.router, prefix="/api")
app.include_router(messages.router, prefix="/api")
app.include_router(inbox.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(health.router, prefix="/api")
