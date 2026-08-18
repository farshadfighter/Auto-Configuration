import uuid
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict

from app.domains.assets.models import AssetStatus, Criticality, ManagedStatus

# psycopg returns INET/MACADDR columns as ipaddress/str-like objects rather than plain str;
# coerce to str so the API always serializes them as strings.
IPString = Annotated[str, BeforeValidator(lambda v: str(v) if v is not None else v)]


class AssetBase(BaseModel):
    name: str
    hostname: str | None = None
    asset_type_id: uuid.UUID
    role_id: uuid.UUID | None = None
    vendor_id: uuid.UUID | None = None
    model: str | None = None
    serial_number: str | None = None
    os_id: uuid.UUID | None = None
    os_version: str | None = None
    management_ip: IPString | None = None
    management_port: int | None = None
    mac_address: IPString | None = None
    location_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    environment_id: uuid.UUID | None = None
    criticality: Criticality = Criticality.MEDIUM
    owner_id: uuid.UUID | None = None
    department: str | None = None
    status: AssetStatus = AssetStatus.UNKNOWN
    managed: ManagedStatus = ManagedStatus.PENDING
    credential_profile_id: uuid.UUID | None = None
    asset_metadata: dict | None = None


class AssetCreate(AssetBase):
    asset_code: str | None = None  # auto-generated when omitted


class AssetUpdate(BaseModel):
    name: str | None = None
    hostname: str | None = None
    role_id: uuid.UUID | None = None
    vendor_id: uuid.UUID | None = None
    model: str | None = None
    serial_number: str | None = None
    os_id: uuid.UUID | None = None
    os_version: str | None = None
    management_ip: str | None = None
    management_port: int | None = None
    mac_address: str | None = None
    location_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    environment_id: uuid.UUID | None = None
    criticality: Criticality | None = None
    owner_id: uuid.UUID | None = None
    department: str | None = None
    status: AssetStatus | None = None
    managed: ManagedStatus | None = None
    credential_profile_id: uuid.UUID | None = None
    asset_metadata: dict | None = None


class AssetOut(AssetBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    asset_code: str
    discovery_source: str | None = None


class AssetRelationshipCreate(BaseModel):
    source_asset_id: uuid.UUID
    target_asset_id: uuid.UUID
    relationship_type: str
    relationship_metadata: dict | None = None


class AssetRelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_asset_id: uuid.UUID
    target_asset_id: uuid.UUID
    relationship_type: str
    relationship_metadata: dict | None = None
    discovery_source: str | None = None
