import csv
import io


def dict_report_to_csv(report: dict) -> str:
    """Flattens a summary report (scalars plus one level of `by_x` breakdown dicts) into a
    two-column metric/value CSV - e.g. `by_status.active,30` - so the same aggregate numbers
    shown on the Reports page can be pulled into a spreadsheet."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["metric", "value"])
    for key, value in report.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                writer.writerow([f"{key}.{sub_key}", sub_value])
        else:
            writer.writerow([key, value if value is not None else ""])
    return buffer.getvalue()


def list_report_to_csv(rows: list[dict]) -> str:
    """Flattens a row-per-record report (currently just technology coverage) into a normal CSV
    table, joining any list-valued cell (e.g. object_types) with semicolons."""
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow({key: "; ".join(value) if isinstance(value, list) else value for key, value in row.items()})
    return buffer.getvalue()
