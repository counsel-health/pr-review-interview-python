## Counsel Chat App

Patient–care-team messaging demo. A Next.js frontend talking to a Django +
Django REST Framework backend over a local PostgreSQL database.

```
frontend/   Next.js app (UI only — it has no server layer of its own)
backend/    Django project: REST API, domain layer, job queue, migrations
docs/       PRODUCT.md, the product rules the code is expected to honor
```

The frontend calls relative `/api/...` URLs and Next proxies them to the
Django server (see `frontend/next.config.mjs`), so the browser never talks to
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
uv run python manage.py migrate
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
cd backend  && uv run python manage.py runserver 8000
cd frontend && yarn dev
```

Open [http://localhost:3000](http://localhost:3000).

4. Optionally run the background job worker in a third terminal:

```bash
cd backend && uv run python manage.py run_worker
```

The worker is a separate process on purpose. Starting it from
`AppConfig.ready()` would spawn one in the autoreloader *and* one in the
reloaded child, giving you two workers competing for the same jobs.

## Backend commands

Run from `backend/`, prefixed with `uv run python manage.py`.

- `migrate` — apply pending migrations (safe to re-run).
- `runserver 8000` — start the API server.
- `run_worker` — poll the job queue and run handlers until interrupted.
- `db_reset` — delete the local embedded PostgreSQL data directory. Follow it
  with `migrate` to rebuild from scratch.
- `sanity_test` — exercise the domain layer and job queue end to end without a
  browser.

There is also `uv run python scripts/build_seed.py <0001_init.sql>`, which
regenerates the committed seed fixture from the legacy SQL dump. The fixture
is checked in, so this is only needed if the upstream seed changes.

## Frontend scripts

Run from `frontend/`.

- `yarn dev` — start the Next.js development server.
- `yarn build` — create a production build.
- `yarn start` — run the production build (run `yarn build` first).
- `yarn lint` — run ESLint.

## Type checking

The backend is type-annotated and checked with mypy (configured in
`backend/pyproject.toml`):

```bash
cd backend && uv run mypy .
```

## Configuration

Copy `.env.example` for the available environment variables. Everything has a
working default; the file is documentation more than a requirement.
