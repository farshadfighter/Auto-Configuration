import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.discovery.models import DiscoveryJobStatus, DiscoveryMethod


class DiscoveryJobCreate(BaseModel):
    method: DiscoveryMethod
    scope: dict = {}
    credential_profile_id: uuid.UUID | None = None


class DiscoveryJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    method: DiscoveryMethod
    status: DiscoveryJobStatus
    discovered_count: int
    updated_count: int
    failed_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class DiscoveryErrorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    target_id: uuid.UUID | None
    message: str


class DiscoveryResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    target_id: uuid.UUID | None
    asset_id: uuid.UUID | None
    action: str
    normalized_data: dict | None
