import datetime
import uuid
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, field_validator

from app.domains.assets.models import (
    AssetStatus,
    BackupFrequency,
    Criticality,
    InformationClassification,
    ManagedStatus,
    SafePin,
)

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
    safe_pin: SafePin | None = None
    asset_metadata: dict | None = None

    # ---- ISMS / ISO 27001 asset-register fields ----
    information_classification: InformationClassification = InformationClassification.INTERNAL
    custodian_id: uuid.UUID | None = None
    acquired_at: datetime.date | None = None
    warranty_expires_at: datetime.date | None = None
    planned_retirement_at: datetime.date | None = None
    decommissioned_at: datetime.date | None = None
    disposal_method: str | None = None
    disposal_notes: str | None = None
    risk_assessment_ref: str | None = None
    risk_last_reviewed_at: datetime.date | None = None
    backup_required: bool = False
    backup_frequency: BackupFrequency | None = None


class AssetCreate(AssetBase):
    asset_code: str | None = None  # auto-generated when omitted
    compliance_framework_codes: list[str] | None = None


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
    safe_pin: SafePin | None = None
    asset_metadata: dict | None = None

    information_classification: InformationClassification | None = None
    custodian_id: uuid.UUID | None = None
    acquired_at: datetime.date | None = None
    warranty_expires_at: datetime.date | None = None
    planned_retirement_at: datetime.date | None = None
    decommissioned_at: datetime.date | None = None
    disposal_method: str | None = None
    disposal_notes: str | None = None
    risk_assessment_ref: str | None = None
    risk_last_reviewed_at: datetime.date | None = None
    backup_required: bool | None = None
    backup_frequency: BackupFrequency | None = None
    compliance_framework_codes: list[str] | None = None


class AssetOut(AssetBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    asset_code: str
    discovery_source: str | None = None
    compliance_scope: list[str] = []

    @field_validator("compliance_scope", mode="before")
    @classmethod
    def _compliance_scope_codes(cls, v):
        if v and not isinstance(v[0], str):
            return [item.code for item in v]
        return v


class ComplianceFrameworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str


class AssetTypeCreate(BaseModel):
    code: str
    name: str
    category: str | None = None


class AssetTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    category: str | None = None


class VendorCreate(BaseModel):
    name: str


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class LocationCreate(BaseModel):
    name: str
    address: str | None = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    address: str | None = None


class ZoneCreate(BaseModel):
    name: str
    description: str | None = None


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None = None


class OperatingSystemCreate(BaseModel):
    name: str
    vendor_id: uuid.UUID | None = None


class OperatingSystemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    vendor_id: uuid.UUID | None = None


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
