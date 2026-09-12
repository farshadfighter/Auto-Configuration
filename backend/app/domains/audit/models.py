import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class AuditEvent(Base):
    """Append-only audit log. No update/delete API is ever exposed for this table."""

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_object", "object_type", "object_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False)  # SUCCESS | FAILURE
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    related_job: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
