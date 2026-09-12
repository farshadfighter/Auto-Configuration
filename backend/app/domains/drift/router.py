import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.audit.service import record_audit_event
from app.domains.drift import service
from app.domains.drift.schemas import DriftResultOut, DriftRunOut, IgnoreDriftRequest
from app.workers.tasks.drift import execute_drift_run_task

router = APIRouter()


@router.post("/drift/analyze", response_model=None, status_code=status.HTTP_201_CREATED)
def analyze(db: DbSession, current_user=Depends(require_permission("drift.run"))):
    run = service.create_run(db, current_user.id)
    record_audit_event(
        db, user_id=current_user.id, action="DRIFT_ANALYSIS_STARTED", object_type="drift_run", object_id=run.id, result="SUCCESS"
    )
    db.commit()
    execute_drift_run_task.delay(str(run.id))
    db.refresh(run)
    return success(DriftRunOut.model_validate(run).model_dump(mode="json"))


@router.get("/drift/findings", response_model=None)
def list_findings(db: DbSession, status_filter: str | None = None, current_user=Depends(require_permission("drift.view"))):
    results = service.list_drift_results(db, status=status_filter)
    return success([DriftResultOut.model_validate(r).model_dump(mode="json") for r in results])


@router.get("/drift/findings/{drift_id}", response_model=None)
def get_finding(drift_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("drift.view"))):
    result = service.get_drift_result(db, drift_id)
    return success(DriftResultOut.model_validate(result).model_dump(mode="json"))


@router.post("/drift/findings/{drift_id}/accept-current", response_model=None)
def accept_current(drift_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("drift.triage"))):
    result = service.accept_current(db, drift_id)
    record_audit_event(
        db, user_id=current_user.id, action="DRIFT_ACCEPTED", object_type="drift_result", object_id=result.id, result="SUCCESS"
    )
    db.commit()
    return success(DriftResultOut.model_validate(result).model_dump(mode="json"))


@router.post("/drift/findings/{drift_id}/ignore", response_model=None)
def ignore(drift_id: uuid.UUID, payload: IgnoreDriftRequest, db: DbSession, current_user=Depends(require_permission("drift.triage"))):
    result = service.ignore_drift(db, drift_id, payload.reason)
    record_audit_event(
        db, user_id=current_user.id, action="DRIFT_IGNORED", object_type="drift_result", object_id=result.id, result="SUCCESS",
        new_value={"reason": payload.reason},
    )
    db.commit()
    return success(DriftResultOut.model_validate(result).model_dump(mode="json"))


@router.post("/drift/findings/{drift_id}/restore-desired", response_model=None)
def restore_desired(drift_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("drift.triage"))):
    job_id = service.create_remediation_job(db, drift_id, current_user.id)
    record_audit_event(
        db, user_id=current_user.id, action="DRIFT_REMEDIATION_JOB_CREATED", object_type="drift_result", object_id=drift_id, result="SUCCESS",
        new_value={"configuration_job_id": str(job_id)},
    )
    db.commit()
    return success({"drift_id": str(drift_id), "configuration_job_id": str(job_id)})
