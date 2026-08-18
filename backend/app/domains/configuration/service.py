import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.domains.assets.models import Asset
from app.domains.configuration import engine
from app.domains.configuration.models import (
    ChangeTypeDB,
    ConfigurationJob,
    ConfigurationJobTarget,
    ConfigurationObject,
    ConfigurationObjectDependency,
    ConfigurationProfile,
    JobStatus,
    ProfileStatus,
    RiskLevel,
    SourceType,
    ValidationStatus,
)
from app.drivers.registry import get_driver

_SEVERITY_TO_VALIDATION_STATUS = {
    "critical": ValidationStatus.CRITICAL,
    "high": ValidationStatus.HIGH,
    "warning": ValidationStatus.WARNING,
}


def _generate_job_number() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"CFG-{date_part}-{uuid.uuid4().hex[:4].upper()}"


def create_job(
    db: Session,
    *,
    name: str,
    description: str | None,
    source_type: SourceType,
    source_design_version_id: uuid.UUID | None,
    target_asset_ids: list[uuid.UUID],
    justification_ref: str | None,
    environment_id: uuid.UUID | None,
    created_by: uuid.UUID | None,
) -> ConfigurationJob:
    if source_type == SourceType.MANUAL and not (justification_ref or "").strip():
        raise ValidationAppError(
            "JUSTIFICATION_REQUIRED",
            "Manual-mode configuration jobs require a justification_ref (ticket link or reason) "
            "since they have no Architecture Design to trace back to.",
        )
    if source_type == SourceType.DESIGN and not source_design_version_id:
        raise ValidationAppError("SOURCE_DESIGN_VERSION_REQUIRED", "source_design_version_id is required when source_type is 'design'")

    job = ConfigurationJob(
        job_number=_generate_job_number(),
        name=name,
        description=description,
        source_type=source_type,
        source_design_version_id=source_design_version_id,
        justification_ref=justification_ref,
        environment_id=environment_id,
        created_by=created_by,
    )
    db.add(job)
    db.flush()
    for asset_id in target_asset_ids:
        db.add(ConfigurationJobTarget(job_id=job.id, asset_id=asset_id))
    db.flush()
    return job


def get_job(db: Session, job_id: uuid.UUID) -> ConfigurationJob:
    job = db.get(ConfigurationJob, job_id)
    if not job:
        raise NotFoundError("CONFIGURATION_JOB_NOT_FOUND", f"Configuration job {job_id} not found")
    return job


def list_jobs(db: Session, *, page: int = 1, page_size: int = 50) -> tuple[list[ConfigurationJob], int]:
    from sqlalchemy import func

    total = db.scalar(select(func.count()).select_from(ConfigurationJob)) or 0
    items = list(
        db.scalars(select(ConfigurationJob).order_by(ConfigurationJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    )
    return items, total


def _require_status(job: ConfigurationJob, *allowed: JobStatus) -> None:
    if job.status not in allowed:
        raise ConflictError(
            "INVALID_JOB_STATUS",
            f"Configuration job is {job.status.value}; expected one of {[s.value for s in allowed]}",
        )


def add_object(db: Session, job_id: uuid.UUID, data: dict) -> ConfigurationObject:
    job = get_job(db, job_id)
    _require_status(job, JobStatus.DRAFT)
    obj = ConfigurationObject(job_id=job_id, **data)
    db.add(obj)
    db.flush()
    return obj


def list_objects(db: Session, job_id: uuid.UUID) -> list[ConfigurationObject]:
    return list(db.scalars(select(ConfigurationObject).where(ConfigurationObject.job_id == job_id)))


def add_dependency(db: Session, job_id: uuid.UUID, parent_id: uuid.UUID, child_id: uuid.UUID, dependency_type: str) -> None:
    job = get_job(db, job_id)
    _require_status(job, JobStatus.DRAFT)
    for object_id in (parent_id, child_id):
        obj = db.get(ConfigurationObject, object_id)
        if not obj or obj.job_id != job_id:
            raise NotFoundError("CONFIGURATION_OBJECT_NOT_FOUND", f"Configuration object {object_id} not found in this job")
    db.add(ConfigurationObjectDependency(parent_object_id=parent_id, child_object_id=child_id, dependency_type=dependency_type))
    db.flush()


def generate(db: Session, job_id: uuid.UUID) -> ConfigurationJob:
    job = get_job(db, job_id)
    _require_status(job, JobStatus.DRAFT)

    objects = list_objects(db, job_id)
    if not objects:
        raise ValidationAppError("NO_OBJECTS", "Configuration job has no objects to generate")
    object_ids = [o.id for o in objects]
    edges = [
        (d.parent_object_id, d.child_object_id)
        for d in db.scalars(
            select(ConfigurationObjectDependency).where(ConfigurationObjectDependency.parent_object_id.in_(object_ids))
        )
    ]

    try:
        ordered_ids = engine.topological_order(object_ids, edges)
    except engine.DependencyCycleError:
        job.status = JobStatus.FAILED
        # Commit (not just flush) - the router's own db.commit() never runs once this raises,
        # and a bare flush is rolled back when the request-scoped session closes, silently
        # reverting the job to DRAFT and hiding the failure from the caller on the next GET.
        db.commit()
        raise ConflictError("DEPENDENCY_CYCLE", "Configuration object dependencies contain a cycle; cannot generate a plan")

    order_index = {oid: i for i, oid in enumerate(ordered_ids)}
    for obj in objects:
        change_type = engine.compute_change_type(obj.current_state, obj.parameters)
        obj.change_type = ChangeTypeDB(change_type.value)
        obj.expected_state = obj.parameters
        obj.execution_order = order_index[obj.id]

        driver = get_driver(obj.technology)
        operations = driver.generate_operations(obj.object_type, change_type, obj.parameters, obj.current_state)
        obj.rendered_operations = [
            {"sequence": op.sequence, "operation_type": op.operation_type, "rendered_config": op.rendered_config}
            for op in operations
        ]

    job.status = JobStatus.GENERATED
    db.flush()
    return job


def validate(db: Session, job_id: uuid.UUID) -> ConfigurationJob:
    job = get_job(db, job_id)
    _require_status(job, JobStatus.GENERATED)

    objects = list_objects(db, job_id)
    worst_severity = None
    delete_count = 0
    touches_high_criticality_asset = False

    for obj in objects:
        driver = get_driver(obj.technology)
        issues = driver.validate_intent(obj.object_type, obj.parameters)
        obj.validation_issues = [
            {"code": i.code, "severity": i.severity, "field": i.field, "message": i.message} for i in issues
        ]
        severities = {i.severity for i in issues}
        if "critical" in severities:
            obj.validation_status = ValidationStatus.CRITICAL
        elif "high" in severities:
            obj.validation_status = ValidationStatus.HIGH
        elif "warning" in severities:
            obj.validation_status = ValidationStatus.WARNING
        else:
            obj.validation_status = ValidationStatus.PASS_

        if obj.validation_status != ValidationStatus.PASS_:
            rank = {"warning": 1, "high": 2, "critical": 3}[obj.validation_status.value]
            if worst_severity is None or rank > worst_severity[0]:
                worst_severity = (rank, obj.validation_status.value)

        if obj.change_type == ChangeTypeDB.DELETE:
            delete_count += 1

        asset = db.get(Asset, obj.asset_id)
        if asset and asset.criticality.value in ("high", "critical"):
            touches_high_criticality_asset = True

    if worst_severity and worst_severity[1] == "critical":
        job.status = JobStatus.FAILED
    else:
        job.status = JobStatus.VALIDATED

    risk = RiskLevel.LOW
    if delete_count >= 3:
        risk = RiskLevel.HIGH
    elif delete_count >= 1:
        risk = RiskLevel.MEDIUM
    if touches_high_criticality_asset and risk in (RiskLevel.LOW, RiskLevel.MEDIUM):
        risk = RiskLevel.HIGH if risk == RiskLevel.MEDIUM else RiskLevel.MEDIUM
    job.risk_level = risk

    db.flush()
    return job


def get_diff(db: Session, job_id: uuid.UUID) -> list[dict]:
    objects = list_objects(db, job_id)
    return [
        {
            "object_id": str(obj.id),
            "object_type": obj.object_type,
            "technology": obj.technology,
            "change_type": obj.change_type.value if obj.change_type else None,
            "current_state": obj.current_state,
            "desired_state": obj.parameters,
            "diff": engine.diff_fields(obj.current_state, obj.parameters),
        }
        for obj in objects
    ]


def submit_for_approval(db: Session, job_id: uuid.UUID) -> ConfigurationJob:
    job = get_job(db, job_id)
    _require_status(job, JobStatus.VALIDATED)
    job.status = JobStatus.PENDING_APPROVAL
    db.flush()
    return job


# --- Configuration Profiles (spec section 45) ---------------------------------------------


def create_profile(db: Session, *, data: dict, created_by: uuid.UUID | None) -> ConfigurationProfile:
    profile = ConfigurationProfile(**data, created_by=created_by)
    db.add(profile)
    db.flush()
    return profile


def get_profile(db: Session, profile_id: uuid.UUID) -> ConfigurationProfile:
    profile = db.get(ConfigurationProfile, profile_id)
    if not profile:
        raise NotFoundError("PROFILE_NOT_FOUND", f"Configuration profile {profile_id} not found")
    return profile


def list_profiles(db: Session) -> list[ConfigurationProfile]:
    return list(db.scalars(select(ConfigurationProfile)))


def update_profile(db: Session, profile_id: uuid.UUID, data: dict) -> ConfigurationProfile:
    profile = get_profile(db, profile_id)
    if profile.status == ProfileStatus.PUBLISHED:
        raise ConflictError(
            "PROFILE_NOT_EDITABLE",
            "A published profile cannot be edited directly (spec section 47); create a new version instead.",
        )
    for key, value in data.items():
        if value is not None:
            setattr(profile, key, value)
    db.flush()
    return profile


def publish_profile(db: Session, profile_id: uuid.UUID) -> ConfigurationProfile:
    profile = get_profile(db, profile_id)
    profile.status = ProfileStatus.PUBLISHED
    db.flush()
    return profile


def create_new_profile_version(db: Session, profile_id: uuid.UUID, created_by: uuid.UUID | None) -> ConfigurationProfile:
    previous = get_profile(db, profile_id)
    new_version = ConfigurationProfile(
        name=previous.name,
        description=previous.description,
        technology=previous.technology,
        object_type=previous.object_type,
        parameters_template=previous.parameters_template,
        version=previous.version + 1,
        status=ProfileStatus.DRAFT,
        created_by=created_by,
    )
    db.add(new_version)
    db.flush()
    return new_version
