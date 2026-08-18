import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class SourceType(str, enum.Enum):
    DESIGN = "design"
    MANUAL = "manual"


class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    VALIDATING = "validating"
    VALIDATED = "validated"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    READY = "ready"
    FAILED = "failed"


class ChangeTypeDB(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NO_CHANGE = "no_change"


class ValidationStatus(str, enum.Enum):
    PENDING = "pending"
    PASS_ = "pass"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProfileStatus(str, enum.Enum):
    DRAFT = "draft"
    TESTING = "testing"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class ConfigurationJob(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "configuration_jobs"

    job_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="config_source_type", values_callable=_enum_values))
    source_design_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_design_versions.id"), nullable=True
    )
    justification_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # required for Manual mode traceability (spec 122-123) when no design backs the job
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name="config_job_status", values_callable=_enum_values), default=JobStatus.DRAFT)
    environment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("asset_environments.id"), nullable=True)
    risk_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel, name="config_risk_level", values_callable=_enum_values), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class ConfigurationJobTarget(Base):
    __tablename__ = "configuration_job_targets"

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("configuration_jobs.id", ondelete="CASCADE"), primary_key=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)


class ConfigurationObject(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "configuration_objects"

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("configuration_jobs.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    technology: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual")  # manual | design_component
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    current_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expected_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    change_type: Mapped[ChangeTypeDB | None] = mapped_column(Enum(ChangeTypeDB, name="config_change_type", values_callable=_enum_values), nullable=True)
    validation_status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus, name="config_validation_status", values_callable=_enum_values), default=ValidationStatus.PENDING
    )
    validation_issues: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    rendered_operations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    execution_order: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ConfigurationObjectDependency(Base):
    __tablename__ = "configuration_object_dependencies"

    parent_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration_objects.id", ondelete="CASCADE"), primary_key=True
    )
    child_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration_objects.id", ondelete="CASCADE"), primary_key=True
    )
    dependency_type: Mapped[str] = mapped_column(String(50), default="requires")


class ConfigurationProfile(UUIDPKMixin, TimestampMixin, Base):
    """Reusable named default-parameter bundle for an object type (spec section 45), e.g.
    "Secure Access Switch" pre-filling access-port VLAN/portfast/BPDU-guard defaults."""

    __tablename__ = "configuration_profiles"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_profile_name_version"),)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technology: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters_template: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[ProfileStatus] = mapped_column(Enum(ProfileStatus, name="profile_status", values_callable=_enum_values), default=ProfileStatus.DRAFT)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
