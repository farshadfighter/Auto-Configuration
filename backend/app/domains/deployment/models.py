import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class DeploymentStatus(str, enum.Enum):
    QUEUED = "queued"
    PRECHECK = "precheck"
    PRECHECK_FAILED = "precheck_failed"
    BACKUP = "backup"
    BACKUP_FAILED = "backup_failed"
    APPLYING = "applying"
    APPLY_FAILED = "apply_failed"
    VERIFYING = "verifying"
    VERIFY_FAILED = "verify_failed"
    SUCCESS = "success"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    ROLLBACK_FAILED = "rollback_failed"


class DeploymentJob(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "deployment_jobs"

    configuration_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("configuration_jobs.id"), nullable=False)
    status: Mapped[DeploymentStatus] = mapped_column(Enum(DeploymentStatus, name="deployment_status", values_callable=_enum_values), default=DeploymentStatus.QUEUED)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class DeploymentTarget(UUIDPKMixin, Base):
    __tablename__ = "deployment_targets"

    deployment_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_jobs.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")


class DeploymentEvent(UUIDPKMixin, Base):
    __tablename__ = "deployment_events"

    deployment_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_jobs.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeploymentResult(UUIDPKMixin, Base):
    __tablename__ = "deployment_results"

    deployment_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_jobs.id", ondelete="CASCADE"), nullable=False)
    configuration_object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("configuration_objects.id"), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    success: Mapped[bool] = mapped_column(nullable=False)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool | None] = mapped_column(nullable=True)
    verify_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ResourceLock(Base):
    """One active lock per asset (spec section 49/62) - enforces at most one in-flight
    deployment per device. expires_at gives crash recovery: a worker that dies without
    releasing the lock doesn't strand the asset locked forever (spec section 51 TTL note)."""

    __tablename__ = "resource_locks"
    __table_args__ = (UniqueConstraint("asset_id", "lock_type", name="uq_resource_lock_asset_type"),)

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    lock_type: Mapped[str] = mapped_column(String(30), primary_key=True, default="deployment")
    deployment_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_jobs.id", ondelete="CASCADE"))
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
