import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.audit.service import record_audit_event
from app.domains.deployment import service
from app.domains.deployment.schemas import DeploymentEventOut, DeploymentJobCreate, DeploymentJobOut, DeploymentResultOut
from app.workers.tasks.deployment import execute_deployment_task

router = APIRouter()


@router.post("/deployment/jobs", response_model=None, status_code=status.HTTP_201_CREATED)
def create_deployment(payload: DeploymentJobCreate, db: DbSession, current_user=Depends(require_permission("deployment.execute"))):
    deployment = service.create_deployment_job(db, payload.configuration_job_id, current_user.id)
    record_audit_event(
        db, user_id=current_user.id, action="DEPLOYMENT_JOB_CREATED", object_type="deployment_job", object_id=deployment.id, result="SUCCESS"
    )
    db.commit()
    return success(DeploymentJobOut.model_validate(deployment).model_dump(mode="json"))


@router.get("/deployment/jobs", response_model=None)
def list_deployments(db: DbSession, current_user=Depends(require_permission("deployment.view"))):
    deployments = service.list_deployments(db)
    return success([DeploymentJobOut.model_validate(d).model_dump(mode="json") for d in deployments])


@router.get("/deployment/jobs/{deployment_id}", response_model=None)
def get_deployment(deployment_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("deployment.view"))):
    deployment = service.get_deployment(db, deployment_id)
    return success(DeploymentJobOut.model_validate(deployment).model_dump(mode="json"))


@router.post("/deployment/jobs/{deployment_id}/start", response_model=None)
def start_deployment(deployment_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("deployment.execute"))):
    deployment = service.get_deployment(db, deployment_id)
    record_audit_event(
        db, user_id=current_user.id, action="DEPLOYMENT_STARTED", object_type="deployment_job", object_id=deployment.id, result="SUCCESS"
    )
    db.commit()
    execute_deployment_task.delay(str(deployment.id))
    db.refresh(deployment)
    return success(DeploymentJobOut.model_validate(deployment).model_dump(mode="json"))


@router.get("/deployment/jobs/{deployment_id}/events", response_model=None)
def get_events(deployment_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("deployment.view"))):
    events = service.get_events(db, deployment_id)
    return success([DeploymentEventOut.model_validate(e).model_dump(mode="json") for e in events])


@router.get("/deployment/jobs/{deployment_id}/results", response_model=None)
def get_results(deployment_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("deployment.view"))):
    results = service.get_results(db, deployment_id)
    return success([DeploymentResultOut.model_validate(r).model_dump(mode="json") for r in results])
