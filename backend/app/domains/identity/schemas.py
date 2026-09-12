import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    description: str | None = None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None = None
    is_system: bool
    permissions: list[PermissionOut] = []


class RoleCreate(BaseModel):
    name: str
    description: str | None = None
    permission_codes: list[str] = []


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    username: str
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    roles: list[RoleOut] = []


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None
    password: str
    role_ids: list[uuid.UUID] = []


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
