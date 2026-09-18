from fastapi import APIRouter, Depends, Response

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.reporting import csv_export, service

router = APIRouter()


def _report_response(data, filename: str, format: str, as_list: bool = False):
    if format == "csv":
        csv_content = csv_export.list_report_to_csv(data) if as_list else csv_export.dict_report_to_csv(data)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )
    return success(data)


@router.get("/reports/asset-inventory", response_model=None)
def asset_inventory(db: DbSession, format: str = "json", current_user=Depends(require_permission("reports.view"))):
    return _report_response(service.asset_inventory_report(db), "asset_inventory_report", format)


@router.get("/reports/architecture-findings", response_model=None)
def architecture_findings(db: DbSession, format: str = "json", current_user=Depends(require_permission("reports.view"))):
    return _report_response(service.architecture_findings_report(db), "architecture_findings_report", format)


@router.get("/reports/configuration-jobs", response_model=None)
def configuration_jobs(db: DbSession, format: str = "json", current_user=Depends(require_permission("reports.view"))):
    return _report_response(service.configuration_jobs_report(db), "configuration_jobs_report", format)


@router.get("/reports/deployments", response_model=None)
def deployments(db: DbSession, format: str = "json", current_user=Depends(require_permission("reports.view"))):
    return _report_response(service.deployments_report(db), "deployments_report", format)


@router.get("/reports/backups", response_model=None)
def backups(db: DbSession, format: str = "json", current_user=Depends(require_permission("reports.view"))):
    return _report_response(service.backups_report(db), "backups_report", format)


@router.get("/reports/drift", response_model=None)
def drift(db: DbSession, format: str = "json", current_user=Depends(require_permission("reports.view"))):
    return _report_response(service.drift_report(db), "drift_report", format)


@router.get("/reports/technology-coverage", response_model=None)
def technology_coverage(db: DbSession, format: str = "json", current_user=Depends(require_permission("reports.view"))):
    return _report_response(service.technology_coverage_report(db), "technology_coverage_report", format, as_list=True)
