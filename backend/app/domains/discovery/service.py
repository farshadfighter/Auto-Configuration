import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.base import utcnow
from app.domains.assets import service as assets_service
from app.domains.discovery.adapters.base import DiscoveredRecord, DiscoveryAdapter, NotImplementedAdapter
from app.domains.discovery.adapters.csv_import import CsvImportDiscoveryAdapter
from app.domains.discovery.adapters.manual import ManualDiscoveryAdapter
from app.domains.discovery.models import (
    DiscoveryError,
    DiscoveryJob,
    DiscoveryJobStatus,
    DiscoveryMethod,
    DiscoveryResult,
    DiscoveryTarget,
)

IMPLEMENTED_METHODS = {DiscoveryMethod.MANUAL, DiscoveryMethod.CSV_IMPORT}


def get_adapter(db: Session, method: DiscoveryMethod) -> DiscoveryAdapter:
    if method == DiscoveryMethod.MANUAL:
        return ManualDiscoveryAdapter(db)
    if method == DiscoveryMethod.CSV_IMPORT:
        return CsvImportDiscoveryAdapter(db)
    return NotImplementedAdapter(method.value)


def create_discovery_job(
    db: Session, *, method: DiscoveryMethod, scope: dict, created_by: uuid.UUID | None
) -> DiscoveryJob:
    job = DiscoveryJob(method=method, scope=scope, created_by=created_by, status=DiscoveryJobStatus.QUEUED)
    db.add(job)
    db.flush()
    return job


def get_discovery_job(db: Session, job_id: uuid.UUID) -> DiscoveryJob:
    job = db.get(DiscoveryJob, job_id)
    if not job:
        raise NotFoundError("DISCOVERY_JOB_NOT_FOUND", f"Discovery job {job_id} not found")
    return job


def list_discovery_jobs(db: Session, *, page: int = 1, page_size: int = 50) -> tuple[list[DiscoveryJob], int]:
    total = db.scalar(select(func.count()).select_from(DiscoveryJob)) or 0
    items = list(
        db.scalars(
            select(DiscoveryJob).order_by(DiscoveryJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    )
    return items, total


def cancel_discovery_job(db: Session, job_id: uuid.UUID) -> DiscoveryJob:
    job = get_discovery_job(db, job_id)
    if job.status in (DiscoveryJobStatus.SUCCESS, DiscoveryJobStatus.FAILED, DiscoveryJobStatus.CANCELLED):
        return job
    job.status = DiscoveryJobStatus.CANCELLED
    job.completed_at = utcnow()
    db.flush()
    return job


def _reconcile_record(db: Session, job: DiscoveryJob, target: DiscoveryTarget, record: DiscoveredRecord) -> None:
    if record.error:
        db.add(DiscoveryError(discovery_job_id=job.id, target_id=target.id, message=record.error))
        target.status = "failed"
        job.failed_count += 1
        return

    data = dict(record.normalized_data or {})
    duplicate = assets_service.find_duplicate(
        db,
        serial_number=data.get("serial_number"),
        management_ip=data.get("management_ip"),
        hostname=data.get("hostname"),
        mac_address=data.get("mac_address"),
    )
    data["discovery_source"] = job.method.value

    if duplicate:
        asset = assets_service.update_asset(db, duplicate.id, data)
        action = "updated"
        job.updated_count += 1
    else:
        asset = assets_service.create_asset_record(db, data)
        action = "created"
        job.discovered_count += 1

    target.asset_id = asset.id
    target.status = "resolved"
    db.add(
        DiscoveryResult(
            discovery_job_id=job.id,
            target_id=target.id,
            raw_data=record.raw_data,
            normalized_data=record.normalized_data,
            asset_id=asset.id,
            action=action,
        )
    )


def execute_discovery_job(db: Session, job_id: uuid.UUID) -> DiscoveryJob:
    """Runs a discovery job to completion. Synchronous - safe to call directly in tests or
    from the Celery task wrapper (app.workers.tasks.discovery)."""
    job = get_discovery_job(db, job_id)
    if job.status == DiscoveryJobStatus.CANCELLED:
        return job

    job.status = DiscoveryJobStatus.RUNNING
    job.started_at = utcnow()
    db.flush()

    adapter = get_adapter(db, job.method)
    try:
        outcome = adapter.discover(job.scope or {})
    except NotImplementedError as exc:
        job.status = DiscoveryJobStatus.FAILED
        job.completed_at = utcnow()
        db.add(DiscoveryError(discovery_job_id=job.id, target_id=None, message=str(exc)))
        db.flush()
        return job

    for record in outcome.records:
        target = DiscoveryTarget(discovery_job_id=job.id, target=record.target)
        db.add(target)
        db.flush()
        _reconcile_record(db, job, target, record)

    job.completed_at = utcnow()
    if job.failed_count == 0:
        job.status = DiscoveryJobStatus.SUCCESS
    elif job.discovered_count + job.updated_count > 0:
        job.status = DiscoveryJobStatus.PARTIAL
    else:
        job.status = DiscoveryJobStatus.FAILED
    db.flush()
    return job
