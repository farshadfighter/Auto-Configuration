from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.reporting import service

router = APIRouter()


@router.get("/reports/asset-inventory", response_model=None)
def asset_inventory(db: DbSession, current_user=Depends(require_permission("reports.view"))):
    return success(service.asset_inventory_report(db))


@router.get("/reports/architecture-findings", response_model=None)
def architecture_findings(db: DbSession, current_user=Depends(require_permission("reports.view"))):
    return success(service.architecture_findings_report(db))


@router.get("/reports/configuration-jobs", response_model=None)
def configuration_jobs(db: DbSession, current_user=Depends(require_permission("reports.view"))):
    return success(service.configuration_jobs_report(db))


@router.get("/reports/deployments", response_model=None)
def deployments(db: DbSession, current_user=Depends(require_permission("reports.view"))):
    return success(service.deployments_report(db))


@router.get("/reports/backups", response_model=None)
def backups(db: DbSession, current_user=Depends(require_permission("reports.view"))):
    return success(service.backups_report(db))


@router.get("/reports/drift", response_model=None)
def drift(db: DbSession, current_user=Depends(require_permission("reports.view"))):
    return success(service.drift_report(db))


@router.get("/reports/technology-coverage", response_model=None)
def technology_coverage(db: DbSession, current_user=Depends(require_permission("reports.view"))):
    return success(service.technology_coverage_report(db))
