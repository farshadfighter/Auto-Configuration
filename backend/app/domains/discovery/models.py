import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class DiscoveryMethod(str, enum.Enum):
    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    API_IMPORT = "api_import"
    NETWORK_SCAN = "network_scan"
    SNMP = "snmp"
    SSH = "ssh"
    WINRM = "winrm"
    REST_API = "rest_api"
    NETCONF = "netconf"
    RESTCONF = "restconf"
    CLOUD_API = "cloud_api"


class DiscoveryJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PARTIAL = "partial"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DiscoveryJob(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "discovery_jobs"

    method: Mapped[DiscoveryMethod] = mapped_column(
        Enum(DiscoveryMethod, name="discovery_method", values_callable=_enum_values), nullable=False
    )
    status: Mapped[DiscoveryJobStatus] = mapped_column(
        Enum(DiscoveryJobStatus, name="discovery_job_status", values_callable=_enum_values),
        default=DiscoveryJobStatus.QUEUED,
    )
    scope: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    credential_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credential_profiles.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)


class DiscoveryTarget(UUIDPKMixin, Base):
    __tablename__ = "discovery_targets"

    discovery_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_jobs.id", ondelete="CASCADE"), nullable=False
    )
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)


class DiscoveryResult(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "discovery_results"

    discovery_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_jobs.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_targets.id", ondelete="CASCADE"), nullable=True
    )
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    normalized_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # created | updated | skipped | duplicate


class DiscoveryError(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "discovery_errors"

    discovery_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_jobs.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_targets.id", ondelete="CASCADE"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
