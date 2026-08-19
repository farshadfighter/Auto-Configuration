import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError, ValidationAppError
from app.db.base import utcnow
from app.domains.assets.models import Asset
from app.domains.backup import service as backup_service
from app.domains.backup.models import BackupType
from app.domains.configuration import service as configuration_service
from app.domains.configuration.models import ConfigurationJob, ConfigurationObject
from app.domains.configuration.models import JobStatus as ConfigJobStatus
from app.domains.credentials import service as credentials_service
from app.domains.deployment.models import DeploymentEvent, DeploymentJob, DeploymentResult, DeploymentStatus, DeploymentTarget, ResourceLock
from app.domains.drift import service as drift_service
from app.drivers.base import Operation
from app.drivers.registry import get_driver

LOCK_TTL_MINUTES = 15


def _log_event(db: Session, deployment_job_id: uuid.UUID, event_type: str, message: str) -> None:
    db.add(DeploymentEvent(deployment_job_id=deployment_job_id, event_type=event_type, message=message, created_at=utcnow()))
    db.flush()


def create_deployment_job(db: Session, configuration_job_id: uuid.UUID, created_by: uuid.UUID | None) -> DeploymentJob:
    config_job = db.get(ConfigurationJob, configuration_job_id)
    if not config_job:
        raise NotFoundError("CONFIGURATION_JOB_NOT_FOUND", f"Configuration job {configuration_job_id} not found")
    if config_job.status != ConfigJobStatus.APPROVED:
        raise ConflictError("CONFIGURATION_JOB_NOT_APPROVED", f"Configuration job is {config_job.status.value}, not approved")

    objects = list(db.scalars(select(ConfigurationObject).where(ConfigurationObject.job_id == configuration_job_id)))
    if not objects:
        raise ValidationAppError("NO_OBJECTS", "Configuration job has no objects to deploy")

    deployment = DeploymentJob(configuration_job_id=configuration_job_id, created_by=created_by)
    db.add(deployment)
    db.flush()

    for asset_id in {obj.asset_id for obj in objects}:
        db.add(DeploymentTarget(deployment_job_id=deployment.id, asset_id=asset_id))
    db.flush()
    _log_event(db, deployment.id, "created", f"Deployment created from {config_job.job_number}")
    return deployment


def get_deployment(db: Session, deployment_id: uuid.UUID) -> DeploymentJob:
    deployment = db.get(DeploymentJob, deployment_id)
    if not deployment:
        raise NotFoundError("DEPLOYMENT_JOB_NOT_FOUND", f"Deployment job {deployment_id} not found")
    return deployment


def list_deployments(db: Session) -> list[DeploymentJob]:
    return list(db.scalars(select(DeploymentJob).order_by(DeploymentJob.created_at.desc())))


def get_events(db: Session, deployment_id: uuid.UUID) -> list[DeploymentEvent]:
    return list(db.scalars(select(DeploymentEvent).where(DeploymentEvent.deployment_job_id == deployment_id).order_by(DeploymentEvent.created_at)))


def get_results(db: Session, deployment_id: uuid.UUID) -> list[DeploymentResult]:
    return list(db.scalars(select(DeploymentResult).where(DeploymentResult.deployment_job_id == deployment_id)))


def _acquire_locks(db: Session, deployment_id: uuid.UUID, asset_ids: set[uuid.UUID]) -> None:
    now = utcnow()
    for asset_id in asset_ids:
        existing = db.get(ResourceLock, {"asset_id": asset_id, "lock_type": "deployment"})
        if existing and existing.expires_at > now:
            raise ConflictError("RESOURCE_LOCKED", f"Asset {asset_id} already has an active deployment in progress")
        if existing:
            db.delete(existing)
            db.flush()
        db.add(ResourceLock(asset_id=asset_id, lock_type="deployment", deployment_job_id=deployment_id, locked_at=now, expires_at=now + timedelta(minutes=LOCK_TTL_MINUTES)))
    db.flush()


def _release_locks(db: Session, deployment_id: uuid.UUID) -> None:
    locks = list(db.scalars(select(ResourceLock).where(ResourceLock.deployment_job_id == deployment_id)))
    for lock in locks:
        db.delete(lock)
    db.flush()


def _renew_locks(db: Session, deployment_id: uuid.UUID) -> None:
    """Pushes each held lock's expiry out another TTL window. Called at each phase
    transition so a deployment that's still actively running - just slow - never has its
    lock treated as orphaned and stolen by a concurrent deployment on the same asset."""
    now = utcnow()
    locks = list(db.scalars(select(ResourceLock).where(ResourceLock.deployment_job_id == deployment_id)))
    for lock in locks:
        lock.expires_at = now + timedelta(minutes=LOCK_TTL_MINUTES)
    db.flush()


def _fail(db: Session, deployment: DeploymentJob, status: DeploymentStatus, message: str) -> DeploymentJob:
    deployment.status = status
    deployment.completed_at = utcnow()
    _log_event(db, deployment.id, status.value, message)
    _release_locks(db, deployment.id)
    db.flush()
    return deployment


def execute_deployment(db: Session, deployment_id: uuid.UUID) -> DeploymentJob:
    deployment = get_deployment(db, deployment_id)
    objects = list(
        db.scalars(
            select(ConfigurationObject)
            .where(ConfigurationObject.job_id == deployment.configuration_job_id)
            .order_by(ConfigurationObject.execution_order)
        )
    )
    asset_ids = {obj.asset_id for obj in objects}

    try:
        _acquire_locks(db, deployment.id, asset_ids)
    except ConflictError:
        return _fail(db, deployment, DeploymentStatus.PRECHECK_FAILED, "Could not acquire resource lock: asset already locked")

    deployment.status = DeploymentStatus.PRECHECK
    deployment.started_at = utcnow()
    _log_event(db, deployment.id, "precheck_started", f"Checking reachability for {len(asset_ids)} asset(s)")
    db.flush()

    assets_by_id = {a.id: a for a in db.scalars(select(Asset).where(Asset.id.in_(asset_ids)))}
    for asset_id in asset_ids:
        asset = assets_by_id.get(asset_id)
        if not asset or not asset.management_ip or not asset.credential_profile_id:
            return _fail(db, deployment, DeploymentStatus.PRECHECK_FAILED, f"Asset {asset_id} missing management IP or credential profile")

    deployment.status = DeploymentStatus.BACKUP
    _log_event(db, deployment.id, "backup_started", "Taking pre-deployment backup")
    _renew_locks(db, deployment.id)

    backups_by_asset = {}
    for asset_id in asset_ids:
        technology = next(o.technology for o in objects if o.asset_id == asset_id)
        try:
            backups_by_asset[asset_id] = backup_service.create_backup_from_live_device(
                db, asset_id=asset_id, technology=technology, backup_type=BackupType.PRE_DEPLOYMENT, created_by=deployment.created_by
            )
        except AppError as exc:
            return _fail(db, deployment, DeploymentStatus.BACKUP_FAILED, f"Backup failed for asset {asset_id}: {exc.detail}")
    _log_event(db, deployment.id, "backup_completed", f"Backed up {len(backups_by_asset)} asset(s)")

    deployment.status = DeploymentStatus.APPLYING
    _log_event(db, deployment.id, "apply_started", f"Applying {len(objects)} configuration object(s)")
    _renew_locks(db, deployment.id)

    connections: dict[uuid.UUID, object] = {}
    failed_object = None
    for obj in objects:
        asset = assets_by_id[obj.asset_id]
        driver = connections.get(obj.asset_id)
        if driver is None:
            driver = get_driver(obj.technology)
            username = _resolve_username(db, asset.credential_profile_id)
            password = _resolve_password(db, asset.credential_profile_id)
            try:
                driver.connect(host=str(asset.management_ip), port=asset.management_port or 22, username=username, password=password)
            except Exception as exc:
                _log_event(db, deployment.id, "connect_failed", f"{obj.asset_id}: {exc}")
                failed_object = obj
                break
            connections[obj.asset_id] = driver

        operations = [Operation(**op) for op in (obj.rendered_operations or [])]
        result = driver.deploy(operations)
        db.add(DeploymentResult(deployment_job_id=deployment.id, configuration_object_id=obj.id, asset_id=obj.asset_id, success=result.success, output=result.output, error=result.error))
        db.flush()
        _log_event(db, deployment.id, "command_result", f"{obj.object_type} on {obj.asset_id}: {'ok' if result.success else result.error}")
        if not result.success:
            failed_object = obj
            break

    if failed_object is not None:
        for driver in connections.values():
            driver.disconnect()
        return _rollback(db, deployment, backups_by_asset, f"Apply failed on object {failed_object.id}")

    deployment.status = DeploymentStatus.VERIFYING
    _log_event(db, deployment.id, "verification_started", "Verifying applied state")
    _renew_locks(db, deployment.id)

    all_verified = True
    for obj in objects:
        driver = connections[obj.asset_id]
        try:
            verify_result = driver.verify(obj.object_type, obj.parameters)
        except Exception as exc:
            # The device already has the new config applied (apply succeeded above) - a
            # dropped session here means we can't confirm it, not that it failed. Treat as
            # an unconfirmed verification rather than letting the exception escape: an
            # uncaught exception here would propagate to the Celery task's db.rollback(),
            # silently wiping this deployment's whole status trail and its resource locks
            # while the live device has already been changed.
            _log_event(db, deployment.id, "verify_error", f"{obj.object_type} on {obj.asset_id}: {exc}")
            all_verified = False
            continue
        result_row = db.scalar(
            select(DeploymentResult).where(DeploymentResult.deployment_job_id == deployment.id, DeploymentResult.configuration_object_id == obj.id)
        )
        if result_row:
            result_row.verified = verify_result.matches_expected
            result_row.verify_details = verify_result.actual_state
        if verify_result.matches_expected:
            configuration_service.record_version(db, obj, deployment.id, deployment.created_by)
        else:
            all_verified = False
    db.flush()

    for driver in connections.values():
        driver.disconnect()

    if not all_verified:
        return _fail(db, deployment, DeploymentStatus.VERIFY_FAILED, "Post-deployment verification did not match expected state")

    deployment.status = DeploymentStatus.SUCCESS
    deployment.completed_at = utcnow()
    _log_event(db, deployment.id, "completed", "Deployment succeeded")
    _release_locks(db, deployment.id)
    drift_service.mark_remediated_by_configuration_job(db, deployment.configuration_job_id)
    db.flush()
    return deployment


def _resolve_username(db: Session, credential_profile_id: uuid.UUID) -> str:
    return credentials_service.get_credential_profile(db, credential_profile_id).username or ""


def _resolve_password(db: Session, credential_profile_id: uuid.UUID) -> str | None:
    try:
        return credentials_service.resolve_secret(db, credential_profile_id, "password")
    except NotFoundError:
        return None


def _rollback(db: Session, deployment: DeploymentJob, backups_by_asset: dict, reason: str) -> DeploymentJob:
    deployment.status = DeploymentStatus.ROLLING_BACK
    _log_event(db, deployment.id, "rollback_started", reason)
    db.flush()

    all_rolled_back = True
    for asset_id, backup in backups_by_asset.items():
        try:
            backup_service.restore_backup(db, backup.id)
        except AppError as exc:
            all_rolled_back = False
            _log_event(db, deployment.id, "rollback_failed", f"Asset {asset_id}: {exc.detail}")

    status = DeploymentStatus.ROLLED_BACK if all_rolled_back else DeploymentStatus.ROLLBACK_FAILED
    deployment.status = status
    deployment.completed_at = utcnow()
    _log_event(db, deployment.id, status.value, "Rollback finished")
    _release_locks(db, deployment.id)
    db.flush()
    return deployment
