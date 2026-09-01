## Counsel Chat App

Patient–care-team messaging demo. A Next.js frontend talking to a FastAPI
backend over a local PostgreSQL database.

```
frontend/   Next.js app (UI only — it has no server layer of its own)
backend/    FastAPI app: REST API, domain layer, job queue, migrations
docs/       PRODUCT.md, the product rules the code is expected to honor
```

The frontend calls relative `/api/...` URLs and Next proxies them to the
FastAPI server (see `frontend/next.config.mjs`), so the browser never talks to
port 8000 directly.

## Prerequisites

- Node `>=24` (see `.nvmrc`)
- [uv](https://docs.astral.sh/uv/) — it provisions Python 3.13 for you (see
  `.python-version`), so no system Python setup is needed

No PostgreSQL install is required. The backend runs an **embedded** PostgreSQL
server out of `backend/.pgdata/` using [pgembed](https://pypi.org/project/pgembed/),
which ships the server binaries as a wheel. Set `DATABASE_URL` to use a real
PostgreSQL instance instead.

## Getting started

1. Install backend dependencies and create the database:

```bash
cd backend
uv sync
uv run migrate
```

The first `migrate` initializes the embedded PostgreSQL cluster and loads the
seed dataset (1 patient, 2 physicians, 1,201 threads, 11,447 messages).

2. Install frontend dependencies:

```bash
cd ../frontend
yarn
```

3. Run both servers, in two terminals:

```bash
cd backend  && uv run uvicorn app.main:app --port 8000
cd frontend && yarn dev
```

Open [http://localhost:3000](http://localhost:3000).

## The job worker

The API server runs a background job worker from its lifespan, so a job
enqueued by a request is picked up without a second process.

To run the worker on its own instead — which is what a deployment would do —
start it in a third terminal and tell the API server to stand down:

```bash
cd backend && uv run run-worker
cd backend && RUN_WORKER=0 uv run uvicorn app.main:app --port 8000
```

Running both without setting `RUN_WORKER=0` gives you two workers competing
for the same jobs. Either one stops cleanly on Ctrl-C.

## Backend commands

Run from `backend/`.

- `uv run migrate` — apply pending migrations (safe to re-run).
- `uv run uvicorn app.main:app --port 8000` — start the API server. Add
  `--reload` for autoreload during development.
- `uv run run-worker` — poll the job queue and run handlers until interrupted.
- `uv run db-reset` — stop the embedded PostgreSQL server and delete its data
  directory. Follow it with `uv run migrate` to rebuild from scratch.
- `uv run sanity-test` — exercise the domain layer and job queue end to end
  without a browser.

There is also `uv run build-seed <0001_init.sql>`, which regenerates the
committed seed fixture from the legacy SQL dump. The fixture is checked in, so
this is only needed if the upstream seed changes.

## Frontend scripts

Run from `frontend/`.

- `yarn dev` — start the Next.js development server.
- `yarn build` — create a production build.
- `yarn start` — run the production build (run `yarn build` first).
- `yarn lint` — run ESLint.

## Type checking

The backend is type-annotated and checked with mypy in strict mode (configured
in `backend/pyproject.toml`):

```bash
cd backend && uv run mypy .
```

## Configuration

Copy `.env.example` for the available environment variables. Everything has a
working default; the file is documentation more than a requirement.
