import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.deployment.models import DeploymentStatus


class DeploymentJobCreate(BaseModel):
    configuration_job_id: uuid.UUID


class DeploymentJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    configuration_job_id: uuid.UUID
    status: DeploymentStatus
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class DeploymentEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    event_type: str
    message: str
    created_at: datetime


class DeploymentResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    configuration_object_id: uuid.UUID
    asset_id: uuid.UUID
    success: bool
    output: str | None
    error: str | None
    verified: bool | None
