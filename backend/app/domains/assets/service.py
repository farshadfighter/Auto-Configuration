import uuid

from sqlalchemy import cast, func, or_, select
from sqlalchemy.dialects.postgresql import INET, MACADDR
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.domains.assets.models import (
    Asset,
    AssetRelationship,
    AssetType,
    ComplianceFramework,
    Location,
    OperatingSystem,
    Vendor,
    Zone,
)


def _generate_asset_code() -> str:
    return f"AST-{uuid.uuid4().hex[:8].upper()}"


def list_asset_types(db: Session) -> list[AssetType]:
    return list(db.scalars(select(AssetType).order_by(AssetType.name)))


def create_asset_type(db: Session, *, code: str, name: str, category: str | None) -> AssetType:
    if db.scalar(select(AssetType).where(AssetType.code == code)):
        raise ConflictError("ASSET_TYPE_CODE_EXISTS", f"Asset type code '{code}' already exists")
    asset_type = AssetType(code=code, name=name, category=category)
    db.add(asset_type)
    db.flush()
    return asset_type


def list_vendors(db: Session) -> list[Vendor]:
    return list(db.scalars(select(Vendor).order_by(Vendor.name)))


def create_vendor(db: Session, *, name: str) -> Vendor:
    if db.scalar(select(Vendor).where(Vendor.name == name)):
        raise ConflictError("VENDOR_NAME_EXISTS", f"Vendor '{name}' already exists")
    vendor = Vendor(name=name)
    db.add(vendor)
    db.flush()
    return vendor


def list_locations(db: Session) -> list[Location]:
    return list(db.scalars(select(Location).order_by(Location.name)))


def create_location(db: Session, *, name: str, address: str | None) -> Location:
    location = Location(name=name, address=address)
    db.add(location)
    db.flush()
    return location


def list_zones(db: Session) -> list[Zone]:
    """Lists site-less "network zones" - a flat segmentation catalog (VLAN/security-zone
    style) independent of the physical Site hierarchy, matching how the Asset Requirement UI
    presents them. Zone.site_id stays null for entries created here."""
    return list(db.scalars(select(Zone).where(Zone.site_id.is_(None)).order_by(Zone.name)))


def create_zone(db: Session, *, name: str, description: str | None) -> Zone:
    if db.scalar(select(Zone).where(Zone.name == name, Zone.site_id.is_(None))):
        raise ConflictError("ZONE_NAME_EXISTS", f"Network zone '{name}' already exists")
    zone = Zone(name=name, description=description, site_id=None)
    db.add(zone)
    db.flush()
    return zone


def list_operating_systems(db: Session) -> list[OperatingSystem]:
    return list(db.scalars(select(OperatingSystem).order_by(OperatingSystem.name)))


def create_operating_system(db: Session, *, name: str, vendor_id: uuid.UUID | None) -> OperatingSystem:
    vendor_condition = OperatingSystem.vendor_id.is_(None) if vendor_id is None else OperatingSystem.vendor_id == vendor_id
    if db.scalar(select(OperatingSystem).where(OperatingSystem.name == name, vendor_condition)):
        raise ConflictError("OPERATING_SYSTEM_EXISTS", f"Operating system '{name}' already exists for this vendor")
    if vendor_id and not db.get(Vendor, vendor_id):
        raise NotFoundError("VENDOR_NOT_FOUND", f"Vendor {vendor_id} not found")
    operating_system = OperatingSystem(name=name, vendor_id=vendor_id)
    db.add(operating_system)
    db.flush()
    return operating_system


def list_compliance_frameworks(db: Session) -> list[ComplianceFramework]:
    return list(db.scalars(select(ComplianceFramework).order_by(ComplianceFramework.name)))


def resolve_compliance_frameworks(db: Session, codes: list[str]) -> list[ComplianceFramework]:
    frameworks = list(db.scalars(select(ComplianceFramework).where(ComplianceFramework.code.in_(codes))))
    found_codes = {f.code for f in frameworks}
    unknown = set(codes) - found_codes
    if unknown:
        raise NotFoundError("COMPLIANCE_FRAMEWORK_NOT_FOUND", f"Unknown compliance framework code(s): {sorted(unknown)}")
    return frameworks


def find_duplicate(
    db: Session,
    *,
    serial_number: str | None,
    management_ip: str | None,
    hostname: str | None,
    mac_address: str | None,
    exclude_asset_id: uuid.UUID | None = None,
) -> Asset | None:
    """Identity factors per spec: serial number, management IP, hostname, MAC address."""
    conditions = []
    if serial_number:
        conditions.append(Asset.serial_number == serial_number)
    if management_ip:
        # Postgres has no implicit inet = varchar operator; cast the literal explicitly.
        conditions.append(Asset.management_ip == cast(management_ip, INET))
    if hostname:
        conditions.append(Asset.hostname == hostname)
    if mac_address:
        conditions.append(Asset.mac_address == cast(mac_address, MACADDR))
    if not conditions:
        return None

    query = select(Asset).where(or_(*conditions), Asset.deleted_at.is_(None))
    if exclude_asset_id:
        query = query.where(Asset.id != exclude_asset_id)
    return db.scalar(query)


def create_asset_record(db: Session, data: dict) -> Asset:
    """Inserts an asset with no duplicate check. Callers that already resolved a duplicate
    (e.g. discovery reconciliation) use this directly; API callers should use create_asset."""
    data = dict(data)
    asset_code = data.pop("asset_code", None) or _generate_asset_code()
    compliance_codes = data.pop("compliance_framework_codes", None)
    asset = Asset(asset_code=asset_code, **data)
    if compliance_codes is not None:
        asset.compliance_scope = resolve_compliance_frameworks(db, compliance_codes)
    db.add(asset)
    db.flush()
    return asset


def create_asset(db: Session, data: dict) -> Asset:
    duplicate = find_duplicate(
        db,
        serial_number=data.get("serial_number"),
        management_ip=data.get("management_ip"),
        hostname=data.get("hostname"),
        mac_address=data.get("mac_address"),
    )
    if duplicate:
        raise ConflictError(
            "DUPLICATE_ASSET",
            "An asset with the same serial number, management IP, hostname, or MAC address already exists.",
            details={"existing_asset_id": str(duplicate.id), "existing_asset_code": duplicate.asset_code},
        )

    return create_asset_record(db, data)


def get_asset(db: Session, asset_id: uuid.UUID) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.deleted_at.is_(None)))
    if not asset:
        raise NotFoundError("ASSET_NOT_FOUND", f"Asset {asset_id} not found")
    return asset


def list_assets(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    site_id: uuid.UUID | None = None,
    environment_id: uuid.UUID | None = None,
    managed: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> tuple[list[Asset], int]:
    query = select(Asset).where(Asset.deleted_at.is_(None))
    if site_id:
        query = query.where(Asset.site_id == site_id)
    if environment_id:
        query = query.where(Asset.environment_id == environment_id)
    if managed:
        query = query.where(Asset.managed == managed)
    if status:
        query = query.where(Asset.status == status)
    if search:
        like = f"%{search}%"
        query = query.where(or_(Asset.name.ilike(like), Asset.hostname.ilike(like), Asset.asset_code.ilike(like)))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    items = list(
        db.scalars(query.order_by(Asset.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    )
    return items, total


def list_assets_for_export(
    db: Session,
    *,
    site_id: uuid.UUID | None = None,
    environment_id: uuid.UUID | None = None,
    managed: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[Asset]:
    """Same filters as list_assets, but no pagination - an export is expected to be complete,
    not silently truncated to a page."""
    query = select(Asset).where(Asset.deleted_at.is_(None))
    if site_id:
        query = query.where(Asset.site_id == site_id)
    if environment_id:
        query = query.where(Asset.environment_id == environment_id)
    if managed:
        query = query.where(Asset.managed == managed)
    if status:
        query = query.where(Asset.status == status)
    if search:
        like = f"%{search}%"
        query = query.where(or_(Asset.name.ilike(like), Asset.hostname.ilike(like), Asset.asset_code.ilike(like)))
    return list(db.scalars(query.order_by(Asset.asset_code)))


def update_asset(db: Session, asset_id: uuid.UUID, data: dict) -> Asset:
    asset = get_asset(db, asset_id)
    data = dict(data)
    if "compliance_framework_codes" in data:
        codes = data.pop("compliance_framework_codes")
        if codes is not None:
            asset.compliance_scope = resolve_compliance_frameworks(db, codes)
    for key, value in data.items():
        if value is not None:
            setattr(asset, key, value)
    db.flush()
    return asset


def soft_delete_asset(db: Session, asset_id: uuid.UUID) -> None:
    from app.db.base import utcnow

    asset = get_asset(db, asset_id)
    asset.deleted_at = utcnow()
    db.flush()


def create_relationship(db: Session, data: dict) -> AssetRelationship:
    get_asset(db, data["source_asset_id"])
    get_asset(db, data["target_asset_id"])
    relationship = AssetRelationship(**data)
    db.add(relationship)
    db.flush()
    return relationship


def list_relationships(db: Session, asset_id: uuid.UUID) -> list[AssetRelationship]:
    return list(
        db.scalars(
            select(AssetRelationship).where(
                or_(AssetRelationship.source_asset_id == asset_id, AssetRelationship.target_asset_id == asset_id)
            )
        )
    )
