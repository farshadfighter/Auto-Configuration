import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class DesignMode(str, enum.Enum):
    BEST_PRACTICE_ASSISTED = "best_practice_assisted"
    MANUAL = "manual"


class DesignVersionStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class ArchitectureDesign(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "architecture_designs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[DesignMode] = mapped_column(Enum(DesignMode, name="design_mode", values_callable=_enum_values))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class ArchitectureDesignVersion(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "architecture_design_versions"
    __table_args__ = (UniqueConstraint("design_id", "version_number", name="uq_design_version_number"),)

    design_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_designs.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DesignVersionStatus] = mapped_column(
        Enum(DesignVersionStatus, name="design_version_status", values_callable=_enum_values),
        default=DesignVersionStatus.DRAFT,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    @property
    def version_label(self) -> str:
        return f"v{self.version_number}.0"


class DesignComponent(UUIDPKMixin, Base):
    __tablename__ = "design_components"

    design_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_design_versions.id", ondelete="CASCADE"), nullable=False
    )
    component_type: Mapped[str] = mapped_column(String(100), nullable=False)
    technology: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    properties: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    position: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class DesignRelationship(UUIDPKMixin, Base):
    __tablename__ = "design_relationships"

    design_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_design_versions.id", ondelete="CASCADE"), nullable=False
    )
    source_component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("design_components.id", ondelete="CASCADE"), nullable=False
    )
    target_component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("design_components.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_interface: Mapped[str | None] = mapped_column(String(150), nullable=True)
    target_interface: Mapped[str | None] = mapped_column(String(150), nullable=True)


class DesignAssetMapping(Base):
    __tablename__ = "design_asset_mappings"

    design_component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("design_components.id", ondelete="CASCADE"), primary_key=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )


class DesignRecommendationMapping(Base):
    __tablename__ = "design_recommendation_mappings"

    design_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_design_versions.id", ondelete="CASCADE"), primary_key=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_findings.id", ondelete="CASCADE"), primary_key=True
    )


class DesignApproval(UUIDPKMixin, Base):
    __tablename__ = "design_approvals"

    design_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_design_versions.id", ondelete="CASCADE"), nullable=False
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
