import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class ApprovalRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalActionType(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"


class ApprovalRequest(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "approval_requests"

    configuration_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration_jobs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[ApprovalRequestStatus] = mapped_column(
        Enum(ApprovalRequestStatus, name="approval_request_status", values_callable=_enum_values),
        default=ApprovalRequestStatus.PENDING,
    )
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    required_approvals: Mapped[int] = mapped_column(Integer, default=1)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalAction(UUIDPKMixin, Base):
    __tablename__ = "approval_actions"

    approval_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[ApprovalActionType] = mapped_column(Enum(ApprovalActionType, name="approval_action_type", values_callable=_enum_values))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    acted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
