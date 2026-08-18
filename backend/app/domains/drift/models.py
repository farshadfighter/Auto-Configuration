import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPKMixin


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class DriftRunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class DriftSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DriftStatus(str, enum.Enum):
    NEW = "new"
    ACCEPTED = "accepted"
    IGNORED = "ignored"
    REMEDIATED = "remediated"


class DriftRun(UUIDPKMixin, Base):
    __tablename__ = "drift_runs"

    triggered_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status: Mapped[DriftRunStatus] = mapped_column(Enum(DriftRunStatus, name="drift_run_status", values_callable=_enum_values), default=DriftRunStatus.RUNNING)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assets_checked: Mapped[int] = mapped_column(Integer, default=0)
    drift_found_count: Mapped[int] = mapped_column(Integer, default=0)


class DriftResult(UUIDPKMixin, Base):
    __tablename__ = "drift_results"

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drift_runs.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    technology: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    actual_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    diff: Mapped[list] = mapped_column(JSONB, nullable=False)
    severity: Mapped[DriftSeverity] = mapped_column(Enum(DriftSeverity, name="drift_severity", values_callable=_enum_values))
    status: Mapped[DriftStatus] = mapped_column(Enum(DriftStatus, name="drift_status", values_callable=_enum_values), default=DriftStatus.NEW)
    ignore_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
