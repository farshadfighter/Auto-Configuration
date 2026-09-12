import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.best_practice.models import BestPracticeRunStatus, FindingStatus, Severity


class BestPracticeRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: BestPracticeRunStatus
    rules_evaluated: int
    findings_created: int
    started_at: datetime
    completed_at: datetime | None


class ArchitectureFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    finding_code: str
    rule_code: str
    title: str
    technology: str
    category: str
    severity: Severity
    status: FindingStatus
    recommendation: str | None
    ignore_reason: str | None
    detected_at: datetime
    affected_asset_ids: list[uuid.UUID] = []


class IgnoreFindingRequest(BaseModel):
    reason: str
