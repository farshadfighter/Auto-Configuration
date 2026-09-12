import datetime
import enum
import uuid

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, Table, Text, Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET, JSONB, MACADDR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPKMixin


def _enum_values(enum_cls):
    """Persist Python Enum .value (not .name) as the Postgres ENUM labels, matching the
    lowercase strings used across Pydantic schemas and the API."""
    return [e.value for e in enum_cls]


class Criticality(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AssetStatus(str, enum.Enum):
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DECOMMISSIONED = "decommissioned"
    UNKNOWN = "unknown"


class ManagedStatus(str, enum.Enum):
    MANAGED = "managed"
    UNMANAGED = "unmanaged"
    PENDING = "pending"


class InformationClassification(str, enum.Enum):
    """Confidentiality classification per an ISO/IEC 27001-style ISMS (Annex A.5.12/A.5.13) -
    distinct from `criticality`, which rates operational/business impact rather than how
    sensitive the information the asset holds or processes is."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class BackupFrequency(str, enum.Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SafePin(str, enum.Enum):
    """Cisco SAFE-inspired 'Place in the Network' classification, used by the architecture
    recommendation engine (app/domains/architecture_recommendation) to group assets into a
    reference topology. User-assigned; not inferred automatically."""

    INTERNET_EDGE = "internet_edge"
    WAN = "wan"
    CAMPUS_CORE = "campus_core"
    CAMPUS_DISTRIBUTION = "campus_distribution"
    CAMPUS_ACCESS = "campus_access"
    DATA_CENTER = "data_center"
    BRANCH = "branch"
    CLOUD = "cloud"
    MANAGEMENT = "management"


# ---- Lookup / reference tables -------------------------------------------------


class AssetType(UUIDPKMixin, Base):
    __tablename__ = "asset_types"
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)


class AssetRole(UUIDPKMixin, Base):
    __tablename__ = "asset_roles"
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class Vendor(UUIDPKMixin, Base):
    __tablename__ = "vendors"
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)


class OperatingSystem(UUIDPKMixin, Base):
    __tablename__ = "operating_systems"
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    __table_args__ = (UniqueConstraint("vendor_id", "name", name="uq_os_vendor_name"),)


class Location(UUIDPKMixin, Base):
    __tablename__ = "locations"
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Site(UUIDPKMixin, Base):
    __tablename__ = "sites"
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Zone(UUIDPKMixin, Base):
    __tablename__ = "zones"
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (UniqueConstraint("site_id", "name", name="uq_zone_site_name"),)


class ComplianceFramework(UUIDPKMixin, Base):
    """Controlled reference list of regulatory/compliance frameworks an asset can be in scope
    for (ISO 27001, PCI-DSS, GDPR, ...) - deliberately not free text, so "what's in scope for
    PCI-DSS" is a real query an auditor can run, not a grep over a notes field."""

    __tablename__ = "compliance_frameworks"
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)


asset_compliance_scope_map = Table(
    "asset_compliance_scope_map",
    Base.metadata,
    Column("asset_id", UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "compliance_framework_id", UUID(as_uuid=True), ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), primary_key=True
    ),
)


class AssetEnvironment(UUIDPKMixin, Base):
    """Business environment of a managed asset (Production/DR/Staging/...). Not to be confused
    with the deployment environment of NGFabric itself (app.core.config.Settings.environment)."""

    __tablename__ = "asset_environments"
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)


# ---- Tags ------------------------------------------------------------------------


class Tag(UUIDPKMixin, Base):
    __tablename__ = "tags"
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


asset_tag_map = Table(
    "asset_tag_map",
    Base.metadata,
    Column("asset_id", UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


# ---- Core Asset table --------------------------------------------------------------


class Asset(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "assets"

    asset_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    asset_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("asset_types.id"), nullable=False)
    role_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("asset_roles.id"), nullable=True)
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    os_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("operating_systems.id"), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    management_ip: Mapped[str | None] = mapped_column(INET, nullable=True, index=True)
    management_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mac_address: Mapped[str | None] = mapped_column(MACADDR, nullable=True)

    location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    environment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_environments.id"), nullable=True
    )

    criticality: Mapped[Criticality] = mapped_column(
        Enum(Criticality, name="criticality", values_callable=_enum_values), default=Criticality.MEDIUM
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    department: Mapped[str | None] = mapped_column(String(150), nullable=True)

    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status", values_callable=_enum_values), default=AssetStatus.UNKNOWN
    )
    managed: Mapped[ManagedStatus] = mapped_column(
        Enum(ManagedStatus, name="managed_status", values_callable=_enum_values), default=ManagedStatus.PENDING
    )
    credential_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credential_profiles.id"), nullable=True
    )
    discovery_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    safe_pin: Mapped[SafePin | None] = mapped_column(
        Enum(SafePin, name="safe_pin", values_callable=_enum_values), nullable=True
    )

    # ---- ISMS / ISO 27001 asset-register fields (Annex A.5.9 inventory, A.5.12/A.5.13
    # classification, A.7.14 secure disposal) ----------------------------------------------
    information_classification: Mapped[InformationClassification] = mapped_column(
        Enum(InformationClassification, name="information_classification", values_callable=_enum_values),
        default=InformationClassification.INTERNAL,
        nullable=False,
    )
    # The accountable business owner (owner_id, above) is often distinct from whoever does the
    # day-to-day technical administration - both nullable since discovery/CSV-onboarded assets
    # frequently arrive before either is assigned; the asset register still records the gap.
    custodian_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    acquired_at: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    warranty_expires_at: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    planned_retirement_at: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    decommissioned_at: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    disposal_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disposal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk_assessment_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_last_reviewed_at: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)

    backup_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    backup_frequency: Mapped[BackupFrequency | None] = mapped_column(
        Enum(BackupFrequency, name="backup_frequency", values_callable=_enum_values), nullable=True
    )

    asset_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    tags: Mapped[list["Tag"]] = relationship(secondary=asset_tag_map)
    compliance_scope: Mapped[list["ComplianceFramework"]] = relationship(secondary=asset_compliance_scope_map)


class AssetInterface(UUIDPKMixin, Base):
    __tablename__ = "asset_interfaces"
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(MACADDR, nullable=True)
    admin_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    oper_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    speed_mbps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (UniqueConstraint("asset_id", "name", name="uq_interface_asset_name"),)


class AssetIPAddress(UUIDPKMixin, Base):
    __tablename__ = "asset_ip_addresses"
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"))
    interface_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_interfaces.id", ondelete="CASCADE"), nullable=True
    )
    ip_address: Mapped[str] = mapped_column(INET, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


# ---- Groups ------------------------------------------------------------------------


class AssetGroup(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "asset_groups"
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dynamic_rule: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AssetGroupMember(Base):
    __tablename__ = "asset_group_members"
    asset_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_groups.id", ondelete="CASCADE"), primary_key=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )


# ---- Relationships -------------------------------------------------------------------


class AssetRelationship(UUIDPKMixin, Base):
    __tablename__ = "asset_relationships"
    source_asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"))
    target_asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"))
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    relationship_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    discovery_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "source_asset_id", "target_asset_id", "relationship_type", name="uq_asset_relationship"
        ),
    )
