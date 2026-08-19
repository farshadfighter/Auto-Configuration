import ipaddress

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.assets.models import AssetType, Criticality, Vendor
from app.domains.discovery.adapters.base import DiscoveredRecord, DiscoveryAdapter, DiscoveryOutcome


class LookupResolutionMixin:
    """Shared asset_type_code/vendor_name -> id resolution used by manual + CSV adapters."""

    def __init__(self, db: Session):
        self.db = db

    def _resolve_asset_type_id(self, code: str) -> str | None:
        asset_type = self.db.scalar(select(AssetType).where(AssetType.code == code))
        return str(asset_type.id) if asset_type else None

    def _resolve_vendor_id(self, name: str | None) -> str | None:
        if not name:
            return None
        vendor = self.db.scalar(select(Vendor).where(Vendor.name == name))
        return str(vendor.id) if vendor else None

    def _normalize_row(self, row: dict) -> DiscoveredRecord:
        target = row.get("management_ip") or row.get("hostname") or row.get("name", "")
        asset_type_code = row.get("asset_type_code")
        if not asset_type_code:
            return DiscoveredRecord(target=target, raw_data=row, error="asset_type_code is required")

        asset_type_id = self._resolve_asset_type_id(asset_type_code)
        if not asset_type_id:
            return DiscoveredRecord(
                target=target, raw_data=row, error=f"Unknown asset_type_code '{asset_type_code}'"
            )

        criticality = row.get("criticality") or "medium"
        if criticality not in (c.value for c in Criticality):
            # Validate here, before this ever reaches the DB - an invalid value only caught
            # at db.flush() inside create_asset_record/update_asset would raise uncaught in
            # the middle of the import loop, crashing the whole discovery job on one bad row
            # instead of recording it as this row's error.
            return DiscoveredRecord(target=target, raw_data=row, error=f"Invalid criticality '{criticality}'")

        management_ip = row.get("management_ip") or None
        if management_ip:
            try:
                ipaddress.ip_address(management_ip)
            except ValueError:
                return DiscoveredRecord(target=target, raw_data=row, error=f"Invalid management_ip '{management_ip}'")

        normalized = {
            "name": row.get("name") or row.get("hostname") or target,
            "hostname": row.get("hostname"),
            "asset_type_id": asset_type_id,
            "vendor_id": self._resolve_vendor_id(row.get("vendor_name")),
            "management_ip": management_ip,
            "serial_number": row.get("serial_number") or None,
            "mac_address": row.get("mac_address") or None,
            "criticality": criticality,
        }
        return DiscoveredRecord(target=target, raw_data=row, normalized_data=normalized)


class ManualDiscoveryAdapter(LookupResolutionMixin, DiscoveryAdapter):
    """scope = {"records": [{...asset fields...}, ...]}"""

    def discover(self, scope: dict) -> DiscoveryOutcome:
        records = scope.get("records", [])
        return DiscoveryOutcome(records=[self._normalize_row(row) for row in records])

    def normalize(self, record: DiscoveredRecord) -> DiscoveredRecord:
        return record  # already normalized during discover()
