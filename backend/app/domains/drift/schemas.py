import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.drift.models import DriftRunStatus, DriftSeverity, DriftStatus


class DriftRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: DriftRunStatus
    assets_checked: int
    drift_found_count: int
    started_at: datetime
    completed_at: datetime | None


class DriftResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    asset_id: uuid.UUID
    technology: str
    object_type: str
    expected_state: dict
    actual_state: dict
    diff: list
    severity: DriftSeverity
    status: DriftStatus
    ignore_reason: str | None
    detected_at: datetime


class IgnoreDriftRequest(BaseModel):
    reason: str
