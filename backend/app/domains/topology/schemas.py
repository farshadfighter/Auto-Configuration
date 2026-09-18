import uuid

from pydantic import BaseModel, ConfigDict

from app.domains.topology.models import TopologyNodeType, TopologyViewType


class TopologyNodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    node_type: TopologyNodeType
    reference_id: uuid.UUID | None
    label: str
    node_metadata: dict | None = None


class TopologyNodeCreate(BaseModel):
    node_type: TopologyNodeType
    reference_id: uuid.UUID | None = None
    label: str
    node_metadata: dict | None = None


class TopologyLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_node_id: uuid.UUID
    destination_node_id: uuid.UUID
    source_interface: str | None = None
    destination_interface: str | None = None
    link_type: str | None = None
    speed_mbps: int | None = None
    vlan: int | None = None
    subnet: str | None = None
    status: str


class TopologyLinkCreate(BaseModel):
    source_node_id: uuid.UUID
    destination_node_id: uuid.UUID
    source_interface: str | None = None
    destination_interface: str | None = None
    link_type: str | None = None
    speed_mbps: int | None = None
    vlan: int | None = None
    subnet: str | None = None


class TopologyLinkUpdate(BaseModel):
    source_interface: str | None = None
    destination_interface: str | None = None
    link_type: str | None = None
    speed_mbps: int | None = None
    vlan: int | None = None
    subnet: str | None = None


class TopologyGraph(BaseModel):
    nodes: list[TopologyNodeOut]
    links: list[TopologyLinkOut]


class LayoutPosition(BaseModel):
    node_id: uuid.UUID
    x: float
    y: float


class LayoutUpdate(BaseModel):
    view_id: uuid.UUID | None = None
    positions: list[LayoutPosition]


class TopologyViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    view_type: TopologyViewType
    is_default: bool
