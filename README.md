# NGFabric

Infrastructure design, configuration, and change automation platform. See the product and
technical specifications discussed in project history for the full scope; this repository
currently implements **Phase 1: Foundation** per the development order in the technical spec
(section 127) - Auth, RBAC, Assets, Credentials, Audit - as the base the rest of the platform
(Discovery, Topology, Validation, Design, Configuration, Deployment, Backup, Drift) builds on.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, Celery + Redis
- **Frontend**: React 19, TypeScript, Vite, React Query, Zustand, React Router
- **Secrets**: application-level AES-256-GCM envelope encryption (see `app/core/security.py`)

## Quick start (Docker)

```bash
cp .env.example .env
# Generate a secret encryption key and paste it into .env:
python3 -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"

docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.db.seed
```

Backend: http://localhost:8000 (docs at `/docs`) · Frontend: http://localhost:5173

The seed command prints a one-time bootstrap Super Administrator username/password unless
`NGFABRIC_SEED_ADMIN_PASSWORD` is set in the environment.

## Quick start (local, no Docker)

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export NGFABRIC_DATABASE_URL="postgresql+psycopg://ngfabric:ngfabric@localhost:5432/ngfabric"
export NGFABRIC_SECRET_ENCRYPTION_KEY="<generated key>"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Tests

```bash
cd backend
source .venv/bin/activate
createdb ngfabric_test   # once
export NGFABRIC_DATABASE_URL="postgresql+psycopg://ngfabric:ngfabric@localhost:5432/ngfabric_test"
pytest
```

## Repository layout

```
backend/app/
  core/        settings, JWT auth, AES-256-GCM secret encryption, error/response envelopes
  db/          SQLAlchemy session, declarative base, model registry, seed script
  domains/     one package per bounded context (identity, assets, credentials, audit, ...)
  api/v1/      route aggregation, shared dependencies (auth, RBAC)
  workers/     Celery app (job queue - populated as Discovery/Deployment/Backup land)
  alembic/     migrations

frontend/src/
  app/         router
  components/  layout (sidebar, shell)
  modules/     one package per sidebar section (auth, dashboard, assets, audit, ...)
  hooks/       React Query hooks per domain
  services/    API client (axios, standard {success,data,meta} envelope, token refresh)
  stores/      Zustand auth store
```

## What's implemented vs. scaffolded

Implemented and tested: authentication (JWT access + refresh), RBAC (users, groups, roles,
permissions), asset CRUD with duplicate detection and relationships, credential profiles with
encrypted secrets (never returned by the API), hash-chained audit log, the standard API
response/error envelope, and a working frontend against all of it.

Not yet implemented (see the technical spec's phased plan, section 127+): Discovery, Topology,
Best Practice/Validation engines, Architecture Design, Configuration Builder/drivers, Approval
workflow, Deployment workers, Backup, Drift, and Reports. The sidebar shows these as disabled
placeholders so the full information architecture is visible.
