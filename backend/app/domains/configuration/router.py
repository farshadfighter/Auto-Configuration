import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.audit.service import record_audit_event
from app.domains.configuration import service
from app.domains.configuration.schemas import (
    ConfigurationJobCreate,
    ConfigurationJobOut,
    ConfigurationObjectCreate,
    ConfigurationObjectOut,
    DependencyCreate,
    ProfileCreate,
    ProfileOut,
    ProfileUpdate,
)

router = APIRouter()


@router.post("/configuration/jobs", response_model=None, status_code=status.HTTP_201_CREATED)
def create_job(payload: ConfigurationJobCreate, db: DbSession, current_user=Depends(require_permission("configuration.create"))):
    job = service.create_job(
        db,
        name=payload.name,
        description=payload.description,
        source_type=payload.source_type,
        source_design_version_id=payload.source_design_version_id,
        target_asset_ids=payload.target_asset_ids,
        justification_ref=payload.justification_ref,
        environment_id=payload.environment_id,
        created_by=current_user.id,
    )
    record_audit_event(
        db, user_id=current_user.id, action="CONFIG_JOB_CREATED", object_type="configuration_job", object_id=job.id, result="SUCCESS"
    )
    db.commit()
    return success(ConfigurationJobOut.model_validate(job).model_dump(mode="json"))


@router.get("/configuration/jobs", response_model=None)
def list_jobs(db: DbSession, page: int = 1, page_size: int = 50, current_user=Depends(require_permission("configuration.view"))):
    items, total = service.list_jobs(db, page=page, page_size=page_size)
    data = [ConfigurationJobOut.model_validate(j).model_dump(mode="json") for j in items]
    return success(data, meta={"page": page, "page_size": page_size, "total": total})


@router.get("/configuration/jobs/{job_id}", response_model=None)
def get_job(job_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("configuration.view"))):
    job = service.get_job(db, job_id)
    return success(ConfigurationJobOut.model_validate(job).model_dump(mode="json"))


@router.post("/configuration/jobs/{job_id}/objects", response_model=None, status_code=status.HTTP_201_CREATED)
def add_object(job_id: uuid.UUID, payload: ConfigurationObjectCreate, db: DbSession, current_user=Depends(require_permission("configuration.create"))):
    obj = service.add_object(db, job_id, payload.model_dump())
    db.commit()
    return success(ConfigurationObjectOut.model_validate(obj).model_dump(mode="json"))


@router.get("/configuration/jobs/{job_id}/objects", response_model=None)
def list_objects(job_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("configuration.view"))):
    objects = service.list_objects(db, job_id)
    return success([ConfigurationObjectOut.model_validate(o).model_dump(mode="json") for o in objects])


@router.post("/configuration/jobs/{job_id}/dependencies", response_model=None, status_code=status.HTTP_201_CREATED)
def add_dependency(job_id: uuid.UUID, payload: DependencyCreate, db: DbSession, current_user=Depends(require_permission("configuration.create"))):
    service.add_dependency(db, job_id, payload.parent_object_id, payload.child_object_id, payload.dependency_type)
    db.commit()
    return success({"job_id": str(job_id)})


@router.post("/configuration/jobs/{job_id}/generate", response_model=None)
def generate(job_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("configuration.generate"))):
    job = service.generate(db, job_id)
    record_audit_event(
        db, user_id=current_user.id, action="CONFIG_JOB_GENERATED", object_type="configuration_job", object_id=job.id, result="SUCCESS"
    )
    db.commit()
    return success(ConfigurationJobOut.model_validate(job).model_dump(mode="json"))


@router.post("/configuration/jobs/{job_id}/validate", response_model=None)
def validate(job_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("configuration.validate"))):
    job = service.validate(db, job_id)
    record_audit_event(
        db,
        user_id=current_user.id,
        action="CONFIG_JOB_VALIDATED",
        object_type="configuration_job",
        object_id=job.id,
        result="SUCCESS",
        new_value={"status": job.status.value, "risk_level": job.risk_level.value if job.risk_level else None},
    )
    db.commit()
    return success(ConfigurationJobOut.model_validate(job).model_dump(mode="json"))


@router.post("/configuration/profiles", response_model=None, status_code=status.HTTP_201_CREATED)
def create_profile(payload: ProfileCreate, db: DbSession, current_user=Depends(require_permission("configuration.create"))):
    profile = service.create_profile(db, data=payload.model_dump(), created_by=current_user.id)
    db.commit()
    return success(ProfileOut.model_validate(profile).model_dump(mode="json"))


@router.get("/configuration/profiles", response_model=None)
def list_profiles(db: DbSession, current_user=Depends(require_permission("configuration.view"))):
    profiles = service.list_profiles(db)
    return success([ProfileOut.model_validate(p).model_dump(mode="json") for p in profiles])


@router.put("/configuration/profiles/{profile_id}", response_model=None)
def update_profile(profile_id: uuid.UUID, payload: ProfileUpdate, db: DbSession, current_user=Depends(require_permission("configuration.create"))):
    profile = service.update_profile(db, profile_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return success(ProfileOut.model_validate(profile).model_dump(mode="json"))


@router.post("/configuration/profiles/{profile_id}/publish", response_model=None)
def publish_profile(profile_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("configuration.create"))):
    profile = service.publish_profile(db, profile_id)
    db.commit()
    return success(ProfileOut.model_validate(profile).model_dump(mode="json"))


@router.post("/configuration/profiles/{profile_id}/versions", response_model=None, status_code=status.HTTP_201_CREATED)
def create_profile_version(profile_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("configuration.create"))):
    profile = service.create_new_profile_version(db, profile_id, current_user.id)
    db.commit()
    return success(ProfileOut.model_validate(profile).model_dump(mode="json"))


@router.get("/configuration/jobs/{job_id}/diff", response_model=None)
def get_diff(job_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("configuration.view"))):
    return success(service.get_diff(db, job_id))


@router.post("/configuration/jobs/{job_id}/submit-approval", response_model=None)
def submit_for_approval(job_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("configuration.create"))):
    job = service.submit_for_approval(db, job_id)
    record_audit_event(
        db, user_id=current_user.id, action="CONFIG_JOB_SUBMITTED_FOR_APPROVAL", object_type="configuration_job", object_id=job.id, result="SUCCESS"
    )
    db.commit()
    return success(ConfigurationJobOut.model_validate(job).model_dump(mode="json"))
