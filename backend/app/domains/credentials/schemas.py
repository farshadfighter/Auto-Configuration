import uuid

from pydantic import BaseModel, ConfigDict

from app.domains.credentials.models import CredentialType


class CredentialProfileCreate(BaseModel):
    name: str
    description: str | None = None
    credential_type: CredentialType
    username: str | None = None
    secrets: dict[str, str] = {}  # e.g. {"password": "..."} - never echoed back


class CredentialProfileUpdate(BaseModel):
    description: str | None = None
    username: str | None = None
    secrets: dict[str, str] | None = None  # provided keys are rotated/created


class CredentialProfileOut(BaseModel):
    """Secret values are intentionally never included in this schema."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None = None
    credential_type: CredentialType
    username: str | None = None
    secret_keys: list[str] = []
