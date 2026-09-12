import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPKMixin


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class BackupType(str, enum.Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    PRE_DEPLOYMENT = "pre_deployment"
    POST_DEPLOYMENT = "post_deployment"


class Backup(UUIDPKMixin, Base):
    """Configuration snapshot for an asset. Content is stored inline (Text) for MVP; production
    scale should move large configs to object storage and keep only a ref + checksum here
    (spec section 52) - noted as a deliberate simplification, not an oversight."""

    __tablename__ = "backups"

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    technology: Mapped[str] = mapped_column(String(100), nullable=False)
    backup_type: Mapped[BackupType] = mapped_column(Enum(BackupType, name="backup_type", values_callable=_enum_values))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    deployment_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
