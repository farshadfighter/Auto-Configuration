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

        column_count = len(reader.fieldnames)
        records = []
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                # csv.DictReader files extra columns beyond the header under key None as a
                # list - report the ragged row as a per-row error instead of crashing the
                # whole import on a single malformed line.
                records.append(
                    DiscoveredRecord(
                        target=(row.get("name") or "").strip(),
                        raw_data={k: v for k, v in row.items() if k is not None},
                        error=f"Row {line_number} has more columns than the header ({column_count} expected)",
                    )
                )
                continue
            records.append(self._normalize_row({k: (v or "").strip() for k, v in row.items()}))
        return DiscoveryOutcome(records=records)

    def normalize(self, record: DiscoveredRecord) -> DiscoveredRecord:
        return record
