"""Direct CSV bulk export/import for the asset register (ISMS/ISO 27001 asset inventory use
case: an auditor or asset owner exports the whole register, edits it in a spreadsheet, and
re-imports it to update in bulk) - deliberately separate from the Discovery domain's CSV
adapter (app.domains.discovery.adapters.csv_import), which feeds untrusted, review-before-apply
discovery data through a job pipeline. This is a direct, authoritative bulk write by someone who
already holds asset.create/asset.edit, so no review step is needed.

Per-row validation happens fully before any database write for that row, and a row that fails
is recorded as an error without aborting the rest of the file - this codebase has hit the "one
bad row crashes the whole batch" bug several times before (discovery CSV import, manual
discovery rows) and this import path follows the same guard."""

import csv
import datetime
import io
import ipaddress
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domains.assets import service
from app.domains.assets.models import (
    Asset,
    AssetEnvironment,
    AssetStatus,
    AssetType,
    BackupFrequency,
    Criticality,
    InformationClassification,
    Location,
    ManagedStatus,
    OperatingSystem,
    SafePin,
    Site,
    Vendor,
    Zone,
)
from app.domains.identity.models import User
from app.domains.identity.service import get_user_by_username

_MAC_ADDRESS_RE = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")

EXPORT_COLUMNS = [
    "asset_code",
    "name",
    "hostname",
    "asset_type_code",
    "vendor_name",
    "model",
    "serial_number",
    "os_name",
    "os_version",
    "management_ip",
    "management_port",
    "mac_address",
    "location_name",
    "site_name",
    "zone_name",
    "environment_code",
    "criticality",
    "owner_username",
    "custodian_username",
    "department",
    "status",
    "managed",
    "safe_pin",
    "information_classification",
    "compliance_scope",
    "acquired_at",
    "warranty_expires_at",
    "planned_retirement_at",
    "decommissioned_at",
    "disposal_method",
    "disposal_notes",
    "risk_assessment_ref",
    "risk_last_reviewed_at",
    "backup_required",
    "backup_frequency",
]

REQUIRED_IMPORT_COLUMNS = {"name", "asset_type_code"}


class CsvRowError(Exception):
    pass


@dataclass
class ImportSummary:
    created: int = 0
    updated: int = 0
    errors: list[dict] = field(default_factory=list)


# ---- Export -------------------------------------------------------------------------------


def export_assets_to_csv(db: Session, assets: list[Asset]) -> str:
    asset_types = {t.id: t.code for t in db.scalars(select(AssetType))}
    vendors = {v.id: v.name for v in db.scalars(select(Vendor))}
    operating_systems = {o.id: o.name for o in db.scalars(select(OperatingSystem))}
    locations = {location.id: location.name for location in db.scalars(select(Location))}
    sites = {s.id: s.name for s in db.scalars(select(Site))}
    zones = {z.id: z.name for z in db.scalars(select(Zone))}
    environments = {e.id: e.code for e in db.scalars(select(AssetEnvironment))}
    users = {u.id: u.username for u in db.scalars(select(User))}

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS)
    writer.writeheader()
    for asset in assets:
        writer.writerow(
            {
                "asset_code": asset.asset_code,
                "name": asset.name,
                "hostname": asset.hostname or "",
                "asset_type_code": asset_types.get(asset.asset_type_id, ""),
                "vendor_name": vendors.get(asset.vendor_id, "") if asset.vendor_id else "",
                "model": asset.model or "",
                "serial_number": asset.serial_number or "",
                "os_name": operating_systems.get(asset.os_id, "") if asset.os_id else "",
                "os_version": asset.os_version or "",
                "management_ip": str(asset.management_ip) if asset.management_ip else "",
                "management_port": asset.management_port if asset.management_port is not None else "",
                "mac_address": str(asset.mac_address) if asset.mac_address else "",
                "location_name": locations.get(asset.location_id, "") if asset.location_id else "",
                "site_name": sites.get(asset.site_id, "") if asset.site_id else "",
                "zone_name": zones.get(asset.zone_id, "") if asset.zone_id else "",
                "environment_code": environments.get(asset.environment_id, "") if asset.environment_id else "",
                "criticality": asset.criticality.value,
                "owner_username": users.get(asset.owner_id, "") if asset.owner_id else "",
                "custodian_username": users.get(asset.custodian_id, "") if asset.custodian_id else "",
                "department": asset.department or "",
                "status": asset.status.value,
                "managed": asset.managed.value,
                "safe_pin": asset.safe_pin.value if asset.safe_pin else "",
                "information_classification": asset.information_classification.value,
                "compliance_scope": ";".join(f.code for f in asset.compliance_scope),
                "acquired_at": asset.acquired_at.isoformat() if asset.acquired_at else "",
                "warranty_expires_at": asset.warranty_expires_at.isoformat() if asset.warranty_expires_at else "",
                "planned_retirement_at": asset.planned_retirement_at.isoformat() if asset.planned_retirement_at else "",
                "decommissioned_at": asset.decommissioned_at.isoformat() if asset.decommissioned_at else "",
                "disposal_method": asset.disposal_method or "",
                "disposal_notes": asset.disposal_notes or "",
                "risk_assessment_ref": asset.risk_assessment_ref or "",
                "risk_last_reviewed_at": asset.risk_last_reviewed_at.isoformat() if asset.risk_last_reviewed_at else "",
                "backup_required": "true" if asset.backup_required else "false",
                "backup_frequency": asset.backup_frequency.value if asset.backup_frequency else "",
            }
        )
    return buffer.getvalue()


# ---- Import -------------------------------------------------------------------------------


def _get_or_create(db: Session, model, *, lookup: dict, extra: dict | None = None):
    obj = db.scalar(select(model).filter_by(**lookup))
    if not obj:
        obj = model(**lookup, **(extra or {}))
        db.add(obj)
        db.flush()
    return obj


def _parse_date(value: str, field_name: str) -> datetime.date | None:
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise CsvRowError(f"Invalid {field_name} '{value}' - expected YYYY-MM-DD")


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes", "y")


def _parse_enum(value: str, enum_cls, field_name: str):
    if not value:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        allowed = ", ".join(e.value for e in enum_cls)
        raise CsvRowError(f"Invalid {field_name} '{value}' - expected one of: {allowed}")


def _normalize_row(db: Session, row: dict) -> dict:
    """Validates and resolves a raw CSV row into an Asset-ready data dict. Raises CsvRowError
    (never lets an invalid value reach db.flush() uncaught) on any problem."""
    name = row.get("name") or row.get("hostname") or ""
    if not name:
        raise CsvRowError("name (or hostname) is required")

    asset_type_code = row.get("asset_type_code")
    if not asset_type_code:
        raise CsvRowError("asset_type_code is required")
    asset_type = db.scalar(select(AssetType).where(AssetType.code == asset_type_code))
    if not asset_type:
        raise CsvRowError(f"Unknown asset_type_code '{asset_type_code}'")

    management_ip = row.get("management_ip") or None
    if management_ip:
        try:
            ipaddress.ip_address(management_ip)
        except ValueError:
            raise CsvRowError(f"Invalid management_ip '{management_ip}'")

    mac_address = row.get("mac_address") or None
    if mac_address and not _MAC_ADDRESS_RE.match(mac_address):
        raise CsvRowError(f"Invalid mac_address '{mac_address}'")

    management_port = None
    if row.get("management_port"):
        try:
            management_port = int(row["management_port"])
        except ValueError:
            raise CsvRowError(f"Invalid management_port '{row['management_port']}'")

    criticality = _parse_enum(row.get("criticality") or "medium", Criticality, "criticality")
    status = _parse_enum(row.get("status") or "unknown", AssetStatus, "status")
    managed = _parse_enum(row.get("managed") or "pending", ManagedStatus, "managed")
    safe_pin = _parse_enum(row.get("safe_pin") or "", SafePin, "safe_pin")
    information_classification = _parse_enum(
        row.get("information_classification") or "internal", InformationClassification, "information_classification"
    )
    backup_frequency = _parse_enum(row.get("backup_frequency") or "", BackupFrequency, "backup_frequency")

    owner_id = None
    if row.get("owner_username"):
        owner = get_user_by_username(db, row["owner_username"])
        if not owner:
            raise CsvRowError(f"Unknown owner_username '{row['owner_username']}'")
        owner_id = owner.id

    custodian_id = None
    if row.get("custodian_username"):
        custodian = get_user_by_username(db, row["custodian_username"])
        if not custodian:
            raise CsvRowError(f"Unknown custodian_username '{row['custodian_username']}'")
        custodian_id = custodian.id

    compliance_codes = [c.strip() for c in (row.get("compliance_scope") or "").split(";") if c.strip()]
    if compliance_codes:
        # Raises NotFoundError (a clean AppError) for an unknown code - let the caller's
        # per-row exception handler catch it same as CsvRowError.
        service.resolve_compliance_frameworks(db, compliance_codes)

    vendor = _get_or_create(db, Vendor, lookup={"name": row["vendor_name"]}) if row.get("vendor_name") else None
    operating_system = (
        _get_or_create(db, OperatingSystem, lookup={"vendor_id": None, "name": row["os_name"]}) if row.get("os_name") else None
    )
    location = _get_or_create(db, Location, lookup={"name": row["location_name"]}) if row.get("location_name") else None
    site = _get_or_create(db, Site, lookup={"name": row["site_name"]}) if row.get("site_name") else None
    zone = (
        _get_or_create(db, Zone, lookup={"name": row["zone_name"], "site_id": site.id if site else None})
        if row.get("zone_name")
        else None
    )
    environment = (
        _get_or_create(db, AssetEnvironment, lookup={"code": row["environment_code"]}, extra={"name": row["environment_code"]})
        if row.get("environment_code")
        else None
    )

    return {
        "asset_code": row.get("asset_code") or None,
        "name": name,
        "hostname": row.get("hostname") or None,
        "asset_type_id": asset_type.id,
        "vendor_id": vendor.id if vendor else None,
        "model": row.get("model") or None,
        "serial_number": row.get("serial_number") or None,
        "os_id": operating_system.id if operating_system else None,
        "os_version": row.get("os_version") or None,
        "management_ip": management_ip,
        "management_port": management_port,
        "mac_address": mac_address,
        "location_id": location.id if location else None,
        "site_id": site.id if site else None,
        "zone_id": zone.id if zone else None,
        "environment_id": environment.id if environment else None,
        "criticality": criticality,
        "owner_id": owner_id,
        "custodian_id": custodian_id,
        "department": row.get("department") or None,
        "status": status,
        "managed": managed,
        "safe_pin": safe_pin,
        "information_classification": information_classification,
        "compliance_framework_codes": compliance_codes if compliance_codes else None,
        "acquired_at": _parse_date(row.get("acquired_at") or "", "acquired_at"),
        "warranty_expires_at": _parse_date(row.get("warranty_expires_at") or "", "warranty_expires_at"),
        "planned_retirement_at": _parse_date(row.get("planned_retirement_at") or "", "planned_retirement_at"),
        "decommissioned_at": _parse_date(row.get("decommissioned_at") or "", "decommissioned_at"),
        "disposal_method": row.get("disposal_method") or None,
        "disposal_notes": row.get("disposal_notes") or None,
        "risk_assessment_ref": row.get("risk_assessment_ref") or None,
        "risk_last_reviewed_at": _parse_date(row.get("risk_last_reviewed_at") or "", "risk_last_reviewed_at"),
        "backup_required": _parse_bool(row.get("backup_required") or ""),
        "backup_frequency": backup_frequency,
    }


def _process_row(db: Session, row: dict) -> str:
    data = _normalize_row(db, row)
    asset_code = data.get("asset_code")
    existing = None
    if asset_code:
        existing = db.scalar(select(Asset).where(Asset.asset_code == asset_code, Asset.deleted_at.is_(None)))

    if existing:
        service.update_asset(db, existing.id, data)
        return "updated"

    duplicate = service.find_duplicate(
        db,
        serial_number=data.get("serial_number"),
        management_ip=data.get("management_ip"),
        hostname=data.get("hostname"),
        mac_address=data.get("mac_address"),
    )
    if duplicate:
        raise CsvRowError(
            f"An asset with the same serial number, management IP, hostname, or MAC address already exists "
            f"({duplicate.asset_code}) - set asset_code to update it instead"
        )
    service.create_asset_record(db, data)
    return "created"


def import_assets_from_csv(db: Session, csv_content: str) -> ImportSummary:
    summary = ImportSummary()
    reader = csv.DictReader(io.StringIO(csv_content))
    if reader.fieldnames is None or not REQUIRED_IMPORT_COLUMNS.issubset(set(reader.fieldnames)):
        missing = REQUIRED_IMPORT_COLUMNS - set(reader.fieldnames or [])
        summary.errors.append({"row": 1, "message": f"CSV missing required columns: {sorted(missing)}"})
        return summary

    column_count = len(reader.fieldnames)
    for line_number, raw_row in enumerate(reader, start=2):
        if None in raw_row:
            summary.errors.append(
                {"row": line_number, "message": f"Row has more columns than the header ({column_count} expected)"}
            )
            continue

        row = {k: (v or "").strip() for k, v in raw_row.items()}
        savepoint = db.begin_nested()
        try:
            outcome = _process_row(db, row)
            savepoint.commit()
            if outcome == "created":
                summary.created += 1
            else:
                summary.updated += 1
        except (CsvRowError, AppError) as exc:
            savepoint.rollback()
            message = exc.detail["message"] if isinstance(exc, AppError) and isinstance(exc.detail, dict) else str(exc)
            summary.errors.append({"row": line_number, "message": message})
        except Exception as exc:  # noqa: BLE001 - a single bad row (incl. a DB-level
            # constraint violation) must never abort the rest of the import; this is the same
            # guard this codebase has added for every other CSV/bulk-input path so far.
            savepoint.rollback()
            summary.errors.append({"row": line_number, "message": f"Unexpected error: {exc}"})

    return summary
