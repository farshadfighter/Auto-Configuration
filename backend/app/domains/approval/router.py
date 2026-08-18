import uuid

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.approval import service
from app.domains.approval.schemas import ApprovalActionOut, ApprovalRequestOut, ApproveRequest, RejectRequest
from app.domains.audit.service import record_audit_event

router = APIRouter()


@router.get("/approval/requests", response_model=None)
def list_requests(db: DbSession, status_filter: str | None = None, current_user=Depends(require_permission("approval.view"))):
    requests = service.list_requests(db, status=status_filter)
    return success([ApprovalRequestOut.model_validate(r).model_dump(mode="json") for r in requests])


@router.get("/approval/requests/{request_id}", response_model=None)
def get_request(request_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("approval.view"))):
    request = service.get_request(db, request_id)
    data = ApprovalRequestOut.model_validate(request).model_dump(mode="json")
    data["actions"] = [ApprovalActionOut.model_validate(a).model_dump(mode="json") for a in service.get_actions(db, request_id)]
    return success(data)


@router.post("/approval/requests/{request_id}/approve", response_model=None)
def approve(request_id: uuid.UUID, payload: ApproveRequest, db: DbSession, current_user=Depends(require_permission("approval.approve"))):
    request = service.approve(db, request_id, current_user.id, payload.comment)
    record_audit_event(
        db,
        user_id=current_user.id,
        action="APPROVAL_GRANTED",
        object_type="approval_request",
        object_id=request.id,
        result="SUCCESS",
        new_value={"status": request.status.value},
    )
    db.commit()
    return success(ApprovalRequestOut.model_validate(request).model_dump(mode="json"))


@router.post("/approval/requests/{request_id}/reject", response_model=None)
def reject(request_id: uuid.UUID, payload: RejectRequest, db: DbSession, current_user=Depends(require_permission("approval.approve"))):
    request = service.reject(db, request_id, current_user.id, payload.comment)
    record_audit_event(
        db,
        user_id=current_user.id,
        action="APPROVAL_REJECTED",
        object_type="approval_request",
        object_id=request.id,
        result="SUCCESS",
        new_value={"comment": payload.comment},
    )
    db.commit()
    return success(ApprovalRequestOut.model_validate(request).model_dump(mode="json"))
