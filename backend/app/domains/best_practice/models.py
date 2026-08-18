import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Table, Column, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class Severity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(str, enum.Enum):
    NEW = "new"
    IN_REVIEW = "in_review"
    ACCEPTED = "accepted"
    IGNORED = "ignored"
    REMEDIATED = "remediated"
    CLOSED = "closed"


class BestPracticeRunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class BestPracticeRun(UUIDPKMixin, Base):
    __tablename__ = "best_practice_runs"

    triggered_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status: Mapped[BestPracticeRunStatus] = mapped_column(
        Enum(BestPracticeRunStatus, name="best_practice_run_status", values_callable=_enum_values),
        default=BestPracticeRunStatus.RUNNING,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rules_evaluated: Mapped[int] = mapped_column(Integer, default=0)
    findings_created: Mapped[int] = mapped_column(Integer, default=0)


finding_assets = Table(
    "finding_assets",
    Base.metadata,
    Column("finding_id", UUID(as_uuid=True), ForeignKey("architecture_findings.id", ondelete="CASCADE"), primary_key=True),
    Column("asset_id", UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
)


class ArchitectureFinding(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "architecture_findings"

    finding_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("best_practice_runs.id", ondelete="SET NULL"), nullable=True
    )
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    technology: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="finding_severity", values_callable=_enum_values))
    current_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expected_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus, name="finding_status", values_callable=_enum_values), default=FindingStatus.NEW
    )
    ignore_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
