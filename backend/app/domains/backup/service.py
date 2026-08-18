import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.db.base import utcnow
from app.domains.assets import service as assets_service
from app.domains.backup.models import Backup, BackupType
from app.domains.credentials import service as credentials_service
from app.drivers.registry import get_driver


def create_backup(
    db: Session,
    *,
    asset_id: uuid.UUID,
    technology: str,
    backup_type: BackupType,
    content: str,
    created_by: uuid.UUID | None,
    deployment_job_id: uuid.UUID | None = None,
) -> Backup:
    checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
    backup = Backup(
        asset_id=asset_id,
        technology=technology,
        backup_type=backup_type,
        content=content,
        checksum=checksum,
        size_bytes=len(content.encode("utf-8")),
        deployment_job_id=deployment_job_id,
        created_by=created_by,
        created_at=utcnow(),
    )
    db.add(backup)
    db.flush()
    return backup


def create_backup_from_live_device(
    db: Session, *, asset_id: uuid.UUID, technology: str, backup_type: BackupType, created_by: uuid.UUID | None
) -> Backup:
    """Connects to the real device via its driver and pulls the running configuration. Requires
    a reachable asset with a credential profile - the same online path Deployment uses for its
    pre-deployment backup step."""
    asset = assets_service.get_asset(db, asset_id)
    if not asset.credential_profile_id:
        raise AppError(422, "NO_CREDENTIAL_PROFILE", "Asset has no credential profile; cannot connect to pull a live backup")
    if not asset.management_ip:
        raise AppError(422, "NO_MANAGEMENT_IP", "Asset has no management IP; cannot connect to pull a live backup")

    username = credentials_service.get_credential_profile(db, asset.credential_profile_id).username
    password = credentials_service.resolve_secret(db, asset.credential_profile_id, "password")

    driver = get_driver(technology)
    driver.connect(host=str(asset.management_ip), port=asset.management_port or 22, username=username or "", password=password)
    try:
        content = driver.backup()
    finally:
        driver.disconnect()

    return create_backup(db, asset_id=asset_id, technology=technology, backup_type=backup_type, content=content, created_by=created_by)


def get_backup(db: Session, backup_id: uuid.UUID) -> Backup:
    backup = db.get(Backup, backup_id)
    if not backup:
        raise NotFoundError("BACKUP_NOT_FOUND", f"Backup {backup_id} not found")
    return backup


def list_backups_for_asset(db: Session, asset_id: uuid.UUID) -> list[Backup]:
    return list(db.scalars(select(Backup).where(Backup.asset_id == asset_id).order_by(Backup.created_at.desc())))


def restore_backup(db: Session, backup_id: uuid.UUID) -> dict:
    backup = get_backup(db, backup_id)
    asset = assets_service.get_asset(db, backup.asset_id)
    if not asset.credential_profile_id or not asset.management_ip:
        raise AppError(422, "ASSET_NOT_REACHABLE", "Asset has no credential profile or management IP; cannot restore live")

    username = credentials_service.get_credential_profile(db, asset.credential_profile_id).username
    password = credentials_service.resolve_secret(db, asset.credential_profile_id, "password")

    driver = get_driver(backup.technology)
    driver.connect(host=str(asset.management_ip), port=asset.management_port or 22, username=username or "", password=password)
    try:
        result = driver.rollback(backup.content)
    finally:
        driver.disconnect()

    if not result.success:
        raise AppError(502, "RESTORE_FAILED", result.error or "Restore failed", details={"output": result.output})
    return {"backup_id": str(backup.id), "output": result.output}


def compare_backups(db: Session, backup_id_a: uuid.UUID, backup_id_b: uuid.UUID) -> dict:
    a, b = get_backup(db, backup_id_a), get_backup(db, backup_id_b)
    lines_a, lines_b = a.content.splitlines(), b.content.splitlines()
    import difflib

    diff = list(difflib.unified_diff(lines_a, lines_b, fromfile=str(a.id), tofile=str(b.id), lineterm=""))
    return {"backup_a": str(a.id), "backup_b": str(b.id), "diff": diff}
