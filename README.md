# NGFabric

Infrastructure design, configuration, and change automation platform: asset management,
discovery, topology, an architecture best-practice engine, a SAFE-inspired architecture
recommendation engine with real topology-driven path analysis, an editable network diagram,
a driver-based configuration builder, an approval workflow, a deployment engine with backup
and rollback, configuration versioning, drift detection, an ISO 27001/ISMS-style asset
register (with CSV import/export), reporting, and a hash-chained audit log - all behind
authentication and RBAC.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, Celery + Redis
- **Frontend**: React 19, TypeScript, Vite, React Query, Zustand, React Router, React Flow
- **Secrets**: application-level AES-256-GCM envelope encryption (see `app/core/security.py`)
- **CI**: GitHub Actions runs the backend test suite + ruff and the frontend typecheck/build
  on every PR/push to `main` (`.github/workflows/ci.yml`)

## Quick start (Docker) - the fastest way to try it

Needs Docker + Docker Compose installed, and outbound internet access (to pull the
postgres/redis images and install pip/npm packages) on whatever machine you run this on.

```bash
git clone https://github.com/farshadfighter/Auto-Configuration.git
cd Auto-Configuration
cp .env.example .env

# Generate a secret encryption key and paste it into .env as NGFABRIC_SECRET_ENCRYPTION_KEY:
python3 -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"

docker compose up --build
```

Once the containers are up (first build can take a few minutes), in another terminal:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.db.seed
```

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs

The seed command prints a one-time bootstrap Super Administrator username/password to the
console unless `NGFABRIC_SEED_ADMIN_PASSWORD` is set beforehand - copy it now, it is not
shown again. It also seeds the RBAC permission/role matrix, the default asset type catalog,
and the default ISMS compliance-framework catalog (ISO 27001, PCI-DSS, GDPR, HIPAA, SOC 2,
NIST CSF).

`docker compose up` also starts a Celery worker against the same Redis instance, used for
discovery, deployment, and drift analysis jobs.

To stop everything: `docker compose down` (add `-v` to also drop the database volume and
start clean next time).

## ⚠️ Before you rely on this for anything real

This is functionally complete for the scope it was built to, and is safe to stand up and
click through to see how everything fits together. It is **not** production-hardened out of
the box:

- **Change `NGFABRIC_JWT_SECRET_KEY`** in `.env` to a real random secret before exposing this
  beyond your own machine - the default (`change-me-in-production`) is rejected automatically
  for any `NGFABRIC_ENVIRONMENT` other than `development` (the default), but nothing stops you
  from running it insecurely under that default.
- **The device drivers are untested against real hardware.** Cisco IOS-XE, FortiOS, and
  Windows DNS/DHCP each have a real driver implementation (Netmiko/pywinrm-based), but the
  entire test suite exercises them through a `FakeDriver` test double, not physical or
  virtual devices. Test each driver against a lab device before pointing it at anything you
  care about.
- **No TLS, reverse proxy, or rate limiting is configured.** `docker-compose.yml` is a local
  dev setup (plain HTTP, ports exposed directly) - put a real reverse proxy / TLS termination
  in front of it for anything beyond your own workstation.
- **Login lockout exists (5 failed attempts) but there's no broader rate limiting** on other
  endpoints (e.g. the CSV import endpoint, which can run arbitrary DB writes per row).

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
pytest      # 137 tests
ruff check .
```

```bash
cd frontend
npm run build   # tsc -b && vite build - fails on type errors
```

Tests cover every domain individually plus one full end-to-end acceptance test
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
               design, architecture_recommendation, configuration, approval, deployment,
               backup, drift, reporting
  drivers/     technology driver ABC + registry, and concrete drivers:
               cisco_iosxe, fortios, windows_dns, windows_dhcp
  api/v1/      route aggregation, shared dependencies (auth, RBAC)
  workers/     Celery app + tasks for discovery, deployment, and drift jobs
  alembic/     migrations

frontend/src/
  app/         router
  components/  layout (sidebar, shell), shared DeviceIcon
  modules/     one package per sidebar section:
               auth, dashboard, assets, discovery, topology, validation, design,
               configuration, deployment, drift, reports, audit
  hooks/       React Query hooks per domain
  services/    API client (axios, standard {success,data,meta} envelope, token refresh)
  stores/      Zustand auth store

.github/workflows/ci.yml   CI: backend tests+lint, frontend typecheck+build
```

## What's implemented

Every domain in the original MVP scope is implemented, tested, and wired into the frontend:

- **Identity & RBAC**: JWT access/refresh auth with a login lockout after 5 failed attempts,
  users/groups/roles/permissions, `require_permission()` enforcement, seeded roles from Super
  Administrator down to Viewer.
- **Assets & Credentials**: asset CRUD (UI form, not just API/CSV) with duplicate detection
  and relationships, a seeded asset type catalog, and encrypted credential profiles (secrets
  never returned by the API).
- **ISMS / ISO 27001 asset register**: information classification (public/internal/
  confidential/restricted, distinct from operational criticality), a custodian separate from
  the business owner, asset lifecycle dates (acquired/warranty/planned retirement/
  decommissioned) with disposal method/notes, a risk assessment reference + last-reviewed
  date, a declarative backup policy, and a controlled compliance-framework scope (ISO 27001,
  PCI-DSS, GDPR, HIPAA, SOC 2, NIST CSF). Bulk **CSV import/export** for the whole register,
  matching-or-creating by asset code, with per-row validation so one bad row never aborts the
  rest of the file.
- **Discovery**: CSV-import discovery jobs that reconcile discovered devices against existing
  assets; manual entry is also supported at the API level. Live network scan/SNMP/NETCONF
  discovery methods are modeled but not implemented in this MVP - selecting one fails cleanly
  rather than crashing.
- **Topology**: a real device graph derived from assets and relationships, with manual link
  management and drag-to-reposition layout. A "SAFE View" toggle overlays each node's
  classified SAFE zone and highlights, in red, any real path between two zones where a
  required security capability (e.g. a firewall) isn't actually positioned on that path.
- **Architecture Validation**: a YAML-driven best-practice rule engine that evaluates asset
  and configuration state and produces findings.
- **Architecture Design**: an editable, pnet-style device diagram - real device icons per
  component type, drag a device from a palette straight into inventory, draw a connection
  between two devices to create a real topology relationship, click any device for a detail
  panel with "View Asset" / "Configure" (deep-links into the configuration-job flow scoped to
  that device) / "Add to Inventory" actions, plus the full design/version/approval lifecycle.
- **Architecture Recommendation**: generates a reference architecture from the current asset
  inventory, structured around a SAFE-inspired Places-in-the-Network model. Rather than a
  naive "do we own an asset of this type anywhere" check, it traces the real topology graph
  (BFS over actual links) to verify a security capability is genuinely positioned on the path
  between two zones - so an unused firewall doesn't silently hide a real gap. This is an
  internally authored approximation inspired by the publicly-documented SAFE PIN concept, not
  a reproduction of Cisco's proprietary architecture guides.
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
  from the same data as the rest of the app, plus a dashboard with live counts (assets,
  architecture findings, pending approvals, drift) that link straight to the relevant page.
- **Audit**: a hash-chained, immutable audit log covering every state-changing action above.

The only sidebar sections not yet built out as standalone pages are a cross-asset "Backups &
Configuration" list view (backup history is available per-asset on the Asset detail page) and
a general "Settings" page, which are out of scope for this MVP.
