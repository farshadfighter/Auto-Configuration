from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.assets.models import Asset
from app.domains.backup.models import Backup
from app.domains.best_practice.models import ArchitectureFinding
from app.domains.configuration.models import ConfigurationJob, ConfigurationObject
from app.domains.deployment.models import DeploymentJob
from app.domains.drift.models import DriftResult
from app.drivers.registry import get_driver, list_technologies


def _count_by(db: Session, column) -> dict[str, int]:
    rows = db.execute(select(column, func.count()).group_by(column)).all()
    return {(value.value if hasattr(value, "value") else str(value)): count for value, count in rows}


def asset_inventory_report(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(Asset).where(Asset.deleted_at.is_(None))) or 0
    return {
        "total": total,
        "by_status": _count_by(db, Asset.status),
        "by_managed": _count_by(db, Asset.managed),
        "by_criticality": _count_by(db, Asset.criticality),
    }


def architecture_findings_report(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(ArchitectureFinding)) or 0
    return {
        "total": total,
        "by_severity": _count_by(db, ArchitectureFinding.severity),
        "by_status": _count_by(db, ArchitectureFinding.status),
        "by_category": _count_by(db, ArchitectureFinding.category),
    }


def configuration_jobs_report(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(ConfigurationJob)) or 0
    return {"total": total, "by_status": _count_by(db, ConfigurationJob.status), "by_risk": _count_by(db, ConfigurationJob.risk_level)}


def deployments_report(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(DeploymentJob)) or 0
    by_status = _count_by(db, DeploymentJob.status)
    success = by_status.get("success", 0)
    return {
        "total": total,
        "by_status": by_status,
        "success_rate": round(success / total, 4) if total else None,
    }


def backups_report(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(Backup)) or 0
    assets_with_backup = db.scalar(select(func.count(func.distinct(Backup.asset_id)))) or 0
    return {"total": total, "assets_with_backup": assets_with_backup, "by_type": _count_by(db, Backup.backup_type)}


def drift_report(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(DriftResult)) or 0
    return {"total": total, "by_severity": _count_by(db, DriftResult.severity), "by_status": _count_by(db, DriftResult.status)}


def technology_coverage_report(db: Session) -> list[dict]:
    deployed_asset_counts = dict(
        db.execute(
            select(ConfigurationObject.technology, func.count(func.distinct(ConfigurationObject.asset_id))).group_by(
                ConfigurationObject.technology
            )
        ).all()
    )
    coverage = []
    for technology in list_technologies():
        driver = get_driver(technology)
        coverage.append(
            {
                "technology": technology,
                "vendor": driver.manifest.vendor,
                "object_types": list(driver.manifest.capabilities.keys()),
                "deployed_asset_count": deployed_asset_counts.get(technology, 0),
            }
        )
    return coverage
