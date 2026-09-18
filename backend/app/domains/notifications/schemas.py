import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    title: str
    message: str
    object_type: str | None
    object_id: uuid.UUID | None
    is_read: bool
    created_at: datetime
