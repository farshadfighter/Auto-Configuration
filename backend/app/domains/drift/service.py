import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationAppError
from app.db.base import utcnow
from app.domains.assets import service as assets_service
from app.domains.assets.models import Asset
from app.domains.configuration import service as configuration_service
from app.domains.configuration.engine import diff_fields
from app.domains.configuration.models import ConfigurationVersion
from app.domains.credentials import service as credentials_service
from app.domains.drift.models import DriftResult, DriftRun, DriftRunStatus, DriftSeverity, DriftStatus
from app.drivers.registry import get_driver


def _baseline_keys(db: Session) -> list[tuple[uuid.UUID, str, str]]:
    """Every (asset, technology, object_type) combination that has at least one deployed
    version, i.e. a known-good baseline to drift-check against."""
    rows = db.execute(
        select(ConfigurationVersion.asset_id, ConfigurationVersion.technology, ConfigurationVersion.object_type).distinct()
    )
    return [tuple(row) for row in rows]


def create_run(db: Session, triggered_by: uuid.UUID | None) -> DriftRun:
    run = DriftRun(triggered_by=triggered_by, status=DriftRunStatus.RUNNING, started_at=utcnow())
    db.add(run)
    db.flush()
    return run


def get_run(db: Session, run_id: uuid.UUID) -> DriftRun:
    run = db.get(DriftRun, run_id)
    if not run:
        raise NotFoundError("DRIFT_RUN_NOT_FOUND", f"Drift run {run_id} not found")
    return run


def execute_drift_run(db: Session, run_id: uuid.UUID) -> DriftRun:
    run = get_run(db, run_id)

    try:
        assets_checked = 0
        drift_found = 0
        for asset_id, technology, object_type in _baseline_keys(db):
            asset = db.get(Asset, asset_id)
            if not asset or not asset.management_ip or not asset.credential_profile_id:
                continue
            expected = configuration_service.get_latest_version_state(db, asset_id, technology, object_type)
            if expected is None:
                continue

            assets_checked += 1
            driver = None
            try:
                username = credentials_service.get_credential_profile(db, asset.credential_profile_id).username or ""
                password = credentials_service.resolve_secret(db, asset.credential_profile_id, "password")
                driver = get_driver(technology)
                driver.connect(host=str(asset.management_ip), port=asset.management_port or 22, username=username, password=password)
                actual = driver.get_current_state(object_type, expected)
            except Exception:
                continue
            finally:
                if driver is not None:
                    try:
                        driver.disconnect()
                    except Exception:
                        pass

            diff = diff_fields(actual, expected)
            if not diff:
                continue

            severity = DriftSeverity.HIGH if len(diff) >= 3 else DriftSeverity.MEDIUM if len(diff) >= 2 else DriftSeverity.LOW
            db.add(
                DriftResult(
                    run_id=run.id,
                    asset_id=asset_id,
                    technology=technology,
                    object_type=object_type,
                    expected_state=expected,
                    actual_state=actual or {},
                    diff=diff,
                    severity=severity,
                    status=DriftStatus.NEW,
                    detected_at=utcnow(),
                )
            )
            drift_found += 1

        run.assets_checked = assets_checked
        run.drift_found_count = drift_found
        run.status = DriftRunStatus.SUCCESS
        run.completed_at = utcnow()
        db.flush()
        return run
    except Exception:
        run.status = DriftRunStatus.FAILED
        run.completed_at = utcnow()
        db.commit()
        raise


def list_drift_results(db: Session, *, status: str | None = None) -> list[DriftResult]:
    query = select(DriftResult)
    if status:
        query = query.where(DriftResult.status == status)
    return list(db.scalars(query.order_by(DriftResult.detected_at.desc())))


def get_drift_result(db: Session, drift_id: uuid.UUID) -> DriftResult:
    result = db.get(DriftResult, drift_id)
    if not result:
        raise NotFoundError("DRIFT_RESULT_NOT_FOUND", f"Drift result {drift_id} not found")
    return result


def accept_current(db: Session, drift_id: uuid.UUID) -> DriftResult:
    """Treats the live (actual) state as the new correct baseline going forward."""
    drift = get_drift_result(db, drift_id)
    drift.status = DriftStatus.ACCEPTED
    db.flush()
    return drift


def ignore_drift(db: Session, drift_id: uuid.UUID, reason: str) -> DriftResult:
    if not reason or not reason.strip():
        raise ValidationAppError("IGNORE_REASON_REQUIRED", "A reason is required to ignore a drift finding")
    drift = get_drift_result(db, drift_id)
    drift.status = DriftStatus.IGNORED
    drift.ignore_reason = reason
    db.flush()
    return drift


def create_remediation_job(db: Session, drift_id: uuid.UUID, created_by: uuid.UUID | None) -> uuid.UUID:
    """Creates a draft Configuration Job pre-filled with the expected state, ready to run
    through the normal generate/validate/approve/deploy pipeline (spec section 69: 'Create
    Configuration Job' as a drift action)."""
    drift = get_drift_result(db, drift_id)
    asset = assets_service.get_asset(db, drift.asset_id)
    job = configuration_service.create_job(
        db,
        name=f"Drift remediation: {asset.name} {drift.object_type}",
        description=f"Restores desired state for drift finding {drift.id}",
        source_type=configuration_service.SourceType.MANUAL,
        source_design_version_id=None,
        target_asset_ids=[drift.asset_id],
        justification_ref=f"Drift remediation for finding {drift.id}",
        environment_id=None,
        created_by=created_by,
    )
    configuration_service.add_object(
        db,
        job.id,
        {
            "asset_id": drift.asset_id,
            "technology": drift.technology,
            "object_type": drift.object_type,
            "parameters": drift.expected_state,
            "current_state": drift.actual_state,
            "source": "drift_remediation",
        },
    )
    # Stays NEW (not REMEDIATED) until the remediation job actually deploys successfully -
    # see mark_remediated_by_configuration_job, called from deployment/service.py on success.
    # This keeps the finding actionable (and visible under the "new" filter) if the job is
    # later rejected in approval or fails during deployment, instead of hiding a still-drifted
    # asset behind a status that was never earned.
    drift.remediation_job_id = job.id
    db.flush()
    return job.id


def mark_remediated_by_configuration_job(db: Session, configuration_job_id: uuid.UUID) -> None:
    """Called after a configuration job's deployment fully succeeds - flips any drift finding
    that job was created to remediate over to REMEDIATED."""
    results = list(
        db.scalars(
            select(DriftResult).where(
                DriftResult.remediation_job_id == configuration_job_id, DriftResult.status == DriftStatus.NEW
            )
        )
    )
    for result in results:
        result.status = DriftStatus.REMEDIATED
    db.flush()
