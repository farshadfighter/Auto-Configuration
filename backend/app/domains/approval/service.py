import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.db.base import utcnow
from app.domains.approval.models import ApprovalAction, ApprovalActionType, ApprovalRequest, ApprovalRequestStatus
from app.domains.configuration import service as configuration_service

# Risk-based approval policy (spec section 57: rules based on risk). A dedicated
# approval_policies table with configurable rules is a natural extension once more than one
# policy shape is needed; a fixed mapping is the honest MVP scope for now.
_REQUIRED_APPROVALS_BY_RISK = {"low": 1, "medium": 1, "high": 2, "critical": 2}


def create_request_for_job(db: Session, job_id: uuid.UUID, risk_level: str | None) -> ApprovalRequest:
    risk = risk_level or "low"
    request = ApprovalRequest(
        configuration_job_id=job_id,
        risk_level=risk,
        required_approvals=_REQUIRED_APPROVALS_BY_RISK.get(risk, 1),
    )
    db.add(request)
    db.flush()
    return request


def get_request(db: Session, request_id: uuid.UUID) -> ApprovalRequest:
    request = db.get(ApprovalRequest, request_id)
    if not request:
        raise NotFoundError("APPROVAL_REQUEST_NOT_FOUND", f"Approval request {request_id} not found")
    return request


def list_requests(db: Session, *, status: str | None = None) -> list[ApprovalRequest]:
    query = select(ApprovalRequest)
    if status:
        query = query.where(ApprovalRequest.status == status)
    return list(db.scalars(query.order_by(ApprovalRequest.created_at.desc())))


def get_actions(db: Session, request_id: uuid.UUID) -> list[ApprovalAction]:
    return list(db.scalars(select(ApprovalAction).where(ApprovalAction.approval_request_id == request_id)))


def approve(db: Session, request_id: uuid.UUID, actor_id: uuid.UUID | None, comment: str | None) -> ApprovalRequest:
    request = get_request(db, request_id)
    if request.status != ApprovalRequestStatus.PENDING:
        raise ConflictError("APPROVAL_ALREADY_RESOLVED", f"Approval request is already {request.status.value}")

    job = configuration_service.get_job(db, request.configuration_job_id)
    if actor_id and job.created_by == actor_id:
        raise ConflictError("SELF_APPROVAL_NOT_ALLOWED", "The creator of a configuration job cannot approve their own change")

    existing_approvals = [a for a in get_actions(db, request_id) if a.action == ApprovalActionType.APPROVE]
    if actor_id and any(a.actor_user_id == actor_id for a in existing_approvals):
        raise ConflictError("DUPLICATE_APPROVAL", "This user has already approved this request")

    db.add(ApprovalAction(approval_request_id=request.id, actor_user_id=actor_id, action=ApprovalActionType.APPROVE, comment=comment, acted_at=utcnow()))
    db.flush()

    total_approvals = len(existing_approvals) + 1
    if total_approvals >= request.required_approvals:
        request.status = ApprovalRequestStatus.APPROVED
        request.resolved_at = utcnow()
        configuration_service.mark_approved(db, request.configuration_job_id, actor_id)
    db.flush()
    return request


def reject(db: Session, request_id: uuid.UUID, actor_id: uuid.UUID | None, comment: str) -> ApprovalRequest:
    if not comment or not comment.strip():
        raise ValidationAppError("REJECT_REASON_REQUIRED", "A reason is required to reject a configuration job")
    request = get_request(db, request_id)
    if request.status != ApprovalRequestStatus.PENDING:
        raise ConflictError("APPROVAL_ALREADY_RESOLVED", f"Approval request is already {request.status.value}")

    db.add(ApprovalAction(approval_request_id=request.id, actor_user_id=actor_id, action=ApprovalActionType.REJECT, comment=comment, acted_at=utcnow()))
    request.status = ApprovalRequestStatus.REJECTED
    request.resolved_at = utcnow()
    configuration_service.mark_rejected(db, request.configuration_job_id)
    db.flush()
    return request
