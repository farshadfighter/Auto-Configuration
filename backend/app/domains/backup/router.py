import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.audit.service import record_audit_event
from app.domains.backup import service
from app.domains.backup.schemas import BackupCreate, BackupDetailOut, BackupOut

router = APIRouter()


@router.post("/assets/{asset_id}/backups", response_model=None, status_code=status.HTTP_201_CREATED)
def create_backup(asset_id: uuid.UUID, payload: BackupCreate, db: DbSession, current_user=Depends(require_permission("backup.create"))):
    if payload.content is not None:
        backup = service.create_backup(
            db, asset_id=asset_id, technology=payload.technology, backup_type=payload.backup_type, content=payload.content, created_by=current_user.id
        )
    else:
        backup = service.create_backup_from_live_device(
            db, asset_id=asset_id, technology=payload.technology, backup_type=payload.backup_type, created_by=current_user.id
        )
    record_audit_event(
        db, user_id=current_user.id, action="BACKUP_CREATED", object_type="backup", object_id=backup.id, result="SUCCESS",
        new_value={"checksum": backup.checksum, "backup_type": backup.backup_type.value},
    )
    db.commit()
    return success(BackupOut.model_validate(backup).model_dump(mode="json"))


@router.get("/assets/{asset_id}/backups", response_model=None)
def list_backups(asset_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("backup.view"))):
    backups = service.list_backups_for_asset(db, asset_id)
    return success([BackupOut.model_validate(b).model_dump(mode="json") for b in backups])


@router.get("/backups/compare", response_model=None)
def compare_backups(backup_a: uuid.UUID, backup_b: uuid.UUID, db: DbSession, current_user=Depends(require_permission("backup.view"))):
    return success(service.compare_backups(db, backup_a, backup_b))


@router.get("/backups/{backup_id}", response_model=None)
def get_backup(backup_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("backup.view"))):
    backup = service.get_backup(db, backup_id)
    return success(BackupDetailOut.model_validate(backup).model_dump(mode="json"))


@router.post("/backups/{backup_id}/restore", response_model=None)
def restore_backup(backup_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("backup.restore"))):
    result = service.restore_backup(db, backup_id)
    record_audit_event(
        db, user_id=current_user.id, action="BACKUP_RESTORED", object_type="backup", object_id=backup_id, result="SUCCESS"
    )
    db.commit()
    return success(result)
