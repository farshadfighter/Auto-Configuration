import csv
import io

from app.domains.discovery.adapters.base import DiscoveredRecord, DiscoveryAdapter, DiscoveryOutcome
from app.domains.discovery.adapters.manual import LookupResolutionMixin

REQUIRED_COLUMNS = {"name", "asset_type_code"}


class CsvImportDiscoveryAdapter(LookupResolutionMixin, DiscoveryAdapter):
    """scope = {"csv_content": "name,hostname,asset_type_code,vendor_name,management_ip,
    serial_number,mac_address,criticality\\n..."}"""

    def discover(self, scope: dict) -> DiscoveryOutcome:
        csv_content = scope.get("csv_content", "")
        reader = csv.DictReader(io.StringIO(csv_content))
        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            return DiscoveryOutcome(
                records=[DiscoveredRecord(target="", raw_data={}, error=f"CSV missing required columns: {missing}")]
            )
        records = [self._normalize_row({k: (v or "").strip() for k, v in row.items()}) for row in reader]
        return DiscoveryOutcome(records=records)

    def normalize(self, record: DiscoveredRecord) -> DiscoveredRecord:
        return record
