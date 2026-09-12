# NGFabric

Infrastructure design, configuration, and change automation platform. See the product and
technical specifications discussed in project history for the full scope. This repository
implements the complete MVP feature set from the technical spec's phased plan (section 127):
asset management, discovery, topology, an architecture best-practice engine, architecture
design, a driver-based configuration builder, an approval workflow, a deployment engine with
backup and rollback, configuration versioning, drift detection, reporting, and a hash-chained
audit log - all behind authentication and RBAC.

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
`NGFABRIC_SEED_ADMIN_PASSWORD` is set in the environment. It also seeds the full RBAC
permission/role matrix (39 permissions across 10 roles, from Super Administrator down to
Viewer).

`docker compose up` also starts a Celery worker against the same Redis instance, used for
discovery, deployment, and drift analysis jobs.

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

Celery worker (needed for discovery/deployment/drift jobs, requires Redis running locally):

```bash
cd backend
source .venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info
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

95 tests cover every domain individually plus one full end-to-end acceptance test
(`tests/test_acceptance.py`) that chains asset creation through discovery, topology, best
practice findings, architecture design, configuration generation, approval, deployment,
backup, versioning, drift detection, and audit as a single continuous workflow. Live device
I/O (Netmiko/pywinrm) is exercised through a `FakeDriver` test double rather than real
hardware; the driver interface itself (`app/drivers/base.py`) is what a real device
integration would implement.

## Repository layout

```
backend/app/
  core/        settings, JWT auth, AES-256-GCM secret encryption, error/response envelopes
  db/          SQLAlchemy session, declarative base, model registry, seed script
  domains/     one package per bounded context:
               identity, assets, credentials, audit, discovery, topology, best_practice,
               design, configuration, approval, deployment, backup, drift, reporting
  drivers/     technology driver ABC + registry, and concrete drivers:
               cisco_iosxe, fortios, windows_dns, windows_dhcp
  api/v1/      route aggregation, shared dependencies (auth, RBAC)
  workers/     Celery app + tasks for discovery, deployment, and drift jobs
  alembic/     migrations

frontend/src/
  app/         router
  components/  layout (sidebar, shell)
  modules/     one package per sidebar section:
               auth, dashboard, assets, discovery, topology, validation, design,
               configuration, deployment, drift, reports, audit
  hooks/       React Query hooks per domain
  services/    API client (axios, standard {success,data,meta} envelope, token refresh)
  stores/      Zustand auth store
```

## What's implemented

Every domain in the MVP scope (technical spec section 88) is implemented, tested, and wired
into the frontend:

- **Identity & RBAC**: JWT access/refresh auth with a login lockout after 5 failed attempts,
  users/groups/roles/permissions, `require_permission()` enforcement, 10 seeded roles from
  Super Administrator to Viewer.
- **Assets & Credentials**: asset CRUD (with a UI form, not just API/CSV) with duplicate
  detection and relationships, a seeded asset type catalog (`/asset-types`), and encrypted
  credential profiles (secrets never returned by the API).
- **Discovery**: CSV-import discovery jobs that reconcile discovered devices against existing
  assets. Manual entry is also supported at the API level. Live network scan/SNMP/NETCONF
  discovery methods are modeled (`DiscoveryMethod` enum, driver-agnostic adapter interface)
  but not implemented in this MVP - selecting one fails cleanly rather than crashing.
- **Topology**: graph derived from assets and relationships, with manual link management.
- **Architecture Validation**: a YAML-driven best-practice rule engine that evaluates asset
  and configuration state and produces findings.
- **Architecture Design**: design/version/component lifecycle with an approval flow, and the
  ability to map best-practice findings to design components.
- **Architecture Recommendation**: generates a reference architecture design from the current
  asset inventory, structured around a SAFE-inspired Places-in-the-Network model (Internet
  Edge, WAN, Campus Core/Distribution/Access, Data Center, Branch, Cloud, Management). Assets
  are manually classified by zone (`Asset.safe_pin`); the generated diagram shows classified
  assets as real components and unmet recommended roles (e.g. a PIN with no firewall) as
  dashed placeholders, so gaps are visible directly in the canvas. This is an internally
  authored approximation inspired by the publicly-documented SAFE PIN concept, not a
  reproduction of Cisco's proprietary architecture guides.
- **Configuration Core**: a driver-based configuration builder (Cisco IOS-XE, FortiOS,
  Windows DNS, Windows DHCP) with dependency-ordered generation, schema/capability
  validation, and a desired-state diff engine (create/update/delete/no-change).
- **Approval workflow**: submit-for-approval / approve / reject, with segregation of duties
  (a job's creator cannot approve their own job).
- **Deployment engine**: a full state machine (queued → precheck → backup → applying →
  verifying → success, with dedicated failure states) that takes a pre-deployment backup,
  applies the change through the asset's driver, verifies the result, and rolls back
  automatically on failure. Per-asset resource locking prevents concurrent deployments.
- **Backup**: on-demand and pre-deployment backups per asset, with checksums.
- **Configuration versioning & drift**: successful, verified deployments are recorded as
  configuration history; a drift job compares live device state against the latest recorded
  version and can generate a remediation job to restore the desired state.
- **Reporting**: asset inventory, technology coverage, and deployment outcome reports drawn
  from the same data as the rest of the app (no separate reporting data path).
- **Audit**: a hash-chained, immutable audit log covering every state-changing action above.

The only sidebar sections not yet built out as standalone pages are a cross-asset "Backups &
Configuration" list view (backup history is available per-asset on the Asset detail page; a
dedicated cross-asset page would need a new list-all-backups endpoint) and a general
"Settings" page (spec section 80), which is out of scope for this MVP.
