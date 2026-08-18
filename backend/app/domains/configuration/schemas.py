import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.configuration.models import ChangeTypeDB, JobStatus, ProfileStatus, RiskLevel, SourceType, ValidationStatus


class ConfigurationJobCreate(BaseModel):
    name: str
    description: str | None = None
    source_type: SourceType = SourceType.MANUAL
    source_design_version_id: uuid.UUID | None = None
    target_asset_ids: list[uuid.UUID] = []
    justification_ref: str | None = None
    environment_id: uuid.UUID | None = None


class ConfigurationJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    job_number: str
    name: str
    description: str | None
    source_type: SourceType
    status: JobStatus
    risk_level: RiskLevel | None
    justification_ref: str | None
    created_at: datetime


class ConfigurationObjectCreate(BaseModel):
    asset_id: uuid.UUID
    technology: str
    object_type: str
    parameters: dict
    current_state: dict | None = None
    source: str = "manual"


class ConfigurationObjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    asset_id: uuid.UUID
    technology: str
    object_type: str
    parameters: dict
    current_state: dict | None
    change_type: ChangeTypeDB | None
    validation_status: ValidationStatus
    validation_issues: list | None
    rendered_operations: list | None
    execution_order: int | None


class DependencyCreate(BaseModel):
    parent_object_id: uuid.UUID
    child_object_id: uuid.UUID
    dependency_type: str = "requires"


class ProfileCreate(BaseModel):
    name: str
    description: str | None = None
    technology: str
    object_type: str
    parameters_template: dict


class ProfileUpdate(BaseModel):
    description: str | None = None
    parameters_template: dict | None = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None
    technology: str
    object_type: str
    parameters_template: dict
    status: ProfileStatus
    version: int
