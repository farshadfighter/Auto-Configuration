import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.backup.models import BackupType


class BackupCreate(BaseModel):
    technology: str
    backup_type: BackupType = BackupType.MANUAL
    content: str | None = None  # if omitted, pulls a live backup from the device


class BackupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    asset_id: uuid.UUID
    technology: str
    backup_type: BackupType
    checksum: str
    size_bytes: int
    created_at: datetime


class BackupDetailOut(BackupOut):
    content: str
