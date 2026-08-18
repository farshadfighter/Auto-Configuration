import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class TopologyNodeType(str, enum.Enum):
    DEVICE = "device"
    SERVER = "server"
    SERVICE = "service"
    ZONE = "zone"
    SITE = "site"
    CLOUD = "cloud"
    NETWORK = "network"
    SUBNET = "subnet"
    APPLICATION = "application"


class TopologyViewType(str, enum.Enum):
    PHYSICAL = "physical"
    LOGICAL = "logical"
    LAYER2 = "layer2"
    LAYER3 = "layer3"
    SECURITY = "security"
    SERVICE = "service"
    APPLICATION_DEPENDENCY = "application_dependency"
    SITE = "site"
    ZONE = "zone"


class TopologyNode(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "topology_nodes"
    __table_args__ = (UniqueConstraint("node_type", "reference_id", name="uq_topology_node_reference"),)

    node_type: Mapped[TopologyNodeType] = mapped_column(
        Enum(TopologyNodeType, name="topology_node_type", values_callable=_enum_values), nullable=False
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    node_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class TopologyLink(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "topology_links"

    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topology_nodes.id", ondelete="CASCADE"), nullable=False
    )
    destination_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topology_nodes.id", ondelete="CASCADE"), nullable=False
    )
    source_interface: Mapped[str | None] = mapped_column(String(150), nullable=True)
    destination_interface: Mapped[str | None] = mapped_column(String(150), nullable=True)
    link_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    speed_mbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vlan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subnet: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    discovery_source: Mapped[str | None] = mapped_column(String(100), nullable=True)


class TopologyView(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "topology_views"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    view_type: Mapped[TopologyViewType] = mapped_column(
        Enum(TopologyViewType, name="topology_view_type", values_callable=_enum_values), nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(default=False)


class TopologyLayout(Base):
    __tablename__ = "topology_layouts"

    view_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topology_views.id", ondelete="CASCADE"), primary_key=True
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topology_nodes.id", ondelete="CASCADE"), primary_key=True
    )
    position_x: Mapped[float] = mapped_column(Float, default=0)
    position_y: Mapped[float] = mapped_column(Float, default=0)
