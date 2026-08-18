import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.audit.service import record_audit_event
from app.domains.discovery import service
from app.domains.discovery.models import DiscoveryError, DiscoveryResult
from app.domains.discovery.schemas import DiscoveryErrorOut, DiscoveryJobCreate, DiscoveryJobOut, DiscoveryResultOut
from app.workers.tasks.discovery import execute_discovery_job_task

router = APIRouter()


@router.post("/discovery/jobs", response_model=None, status_code=status.HTTP_201_CREATED)
def create_discovery_job(
    payload: DiscoveryJobCreate, db: DbSession, current_user=Depends(require_permission("discovery.manage"))
):
    job = service.create_discovery_job(
        db, method=payload.method, scope=payload.scope, created_by=current_user.id
    )
    record_audit_event(
        db,
        user_id=current_user.id,
        action="DISCOVERY_JOB_CREATED",
        object_type="discovery_job",
        object_id=job.id,
        result="SUCCESS",
        new_value={"method": job.method.value},
    )
    db.commit()
    execute_discovery_job_task.delay(str(job.id))
    db.refresh(job)
    return success(DiscoveryJobOut.model_validate(job).model_dump(mode="json"))


@router.get("/discovery/jobs", response_model=None)
def list_discovery_jobs(
    db: DbSession, page: int = 1, page_size: int = 50, current_user=Depends(require_permission("discovery.view"))
):
    items, total = service.list_discovery_jobs(db, page=page, page_size=page_size)
    data = [DiscoveryJobOut.model_validate(j).model_dump(mode="json") for j in items]
    return success(data, meta={"page": page, "page_size": page_size, "total": total})


@router.get("/discovery/jobs/{job_id}", response_model=None)
def get_discovery_job(job_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("discovery.view"))):
    job = service.get_discovery_job(db, job_id)
    return success(DiscoveryJobOut.model_validate(job).model_dump(mode="json"))


@router.post("/discovery/jobs/{job_id}/cancel", response_model=None)
def cancel_discovery_job(
    job_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("discovery.manage"))
):
    job = service.cancel_discovery_job(db, job_id)
    record_audit_event(
        db, user_id=current_user.id, action="DISCOVERY_JOB_CANCELLED", object_type="discovery_job", object_id=job.id, result="SUCCESS"
    )
    db.commit()
    return success(DiscoveryJobOut.model_validate(job).model_dump(mode="json"))


@router.get("/discovery/jobs/{job_id}/results", response_model=None)
def list_discovery_results(
    job_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("discovery.view"))
):
    service.get_discovery_job(db, job_id)  # 404 if missing
    results = list(db.scalars(select(DiscoveryResult).where(DiscoveryResult.discovery_job_id == job_id)))
    return success([DiscoveryResultOut.model_validate(r).model_dump(mode="json") for r in results])


@router.get("/discovery/jobs/{job_id}/errors", response_model=None)
def list_discovery_errors(
    job_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("discovery.view"))
):
    service.get_discovery_job(db, job_id)
    errors = list(db.scalars(select(DiscoveryError).where(DiscoveryError.discovery_job_id == job_id)))
    return success([DiscoveryErrorOut.model_validate(e).model_dump(mode="json") for e in errors])
