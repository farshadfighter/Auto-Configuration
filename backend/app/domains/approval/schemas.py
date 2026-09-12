import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.approval.models import ApprovalActionType, ApprovalRequestStatus


class ApprovalRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    configuration_job_id: uuid.UUID
    status: ApprovalRequestStatus
    risk_level: str
    required_approvals: int
    created_at: datetime
    resolved_at: datetime | None


class ApprovalActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: ApprovalActionType
    comment: str | None
    acted_at: datetime


class ApproveRequest(BaseModel):
    comment: str | None = None


class RejectRequest(BaseModel):
    comment: str
