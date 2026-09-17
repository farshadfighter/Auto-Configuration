import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.design.models import DesignMode, DesignVersionStatus


class DesignCreate(BaseModel):
    name: str
    description: str | None = None
    mode: DesignMode = DesignMode.MANUAL


class DesignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None
    mode: DesignMode
    created_at: datetime


class DesignVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    design_id: uuid.UUID
    version_number: int
    version_label: str
    status: DesignVersionStatus
    created_at: datetime


class ComponentCreate(BaseModel):
    component_type: str
    technology: str | None = None
    name: str
    properties: dict | None = None
    position: dict | None = None


class ComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    design_version_id: uuid.UUID
    component_type: str
    technology: str | None
    name: str
    properties: dict | None
    position: dict | None
    asset_id: uuid.UUID | None = None


class RelationshipCreate(BaseModel):
    source_component_id: uuid.UUID
    target_component_id: uuid.UUID
    relationship_type: str
    source_interface: str | None = None
    target_interface: str | None = None


class RelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_component_id: uuid.UUID
    target_component_id: uuid.UUID
    relationship_type: str
    source_interface: str | None = None
    target_interface: str | None = None


class VersionGraph(BaseModel):
    components: list[ComponentOut]
    relationships: list[RelationshipOut]


class ApproveDesignRequest(BaseModel):
    comment: str | None = None


class AssetMappingRequest(BaseModel):
    asset_id: uuid.UUID


class RecommendationMappingRequest(BaseModel):
    finding_id: uuid.UUID
