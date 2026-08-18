import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.audit.service import record_audit_event
from app.domains.credentials import service
from app.domains.credentials.schemas import CredentialProfileCreate, CredentialProfileOut, CredentialProfileUpdate

router = APIRouter()


def _to_out(db: DbSession, profile) -> dict:
    data = CredentialProfileOut.model_validate(profile).model_dump(mode="json")
    data["secret_keys"] = service.get_secret_keys(db, profile.id)
    return data


@router.get("/credentials", response_model=None)
def list_credentials(db: DbSession, current_user=Depends(require_permission("credential.view"))):
    profiles = service.list_credential_profiles(db)
    return success([_to_out(db, p) for p in profiles])


@router.post("/credentials", response_model=None, status_code=status.HTTP_201_CREATED)
def create_credential(
    payload: CredentialProfileCreate, db: DbSession, current_user=Depends(require_permission("credential.manage"))
):
    profile = service.create_credential_profile(
        db,
        name=payload.name,
        description=payload.description,
        credential_type=payload.credential_type,
        username=payload.username,
        secrets=payload.secrets,
    )
    record_audit_event(
        db,
        user_id=current_user.id,
        action="CREDENTIAL_PROFILE_CREATED",
        object_type="credential_profile",
        object_id=profile.id,
        result="SUCCESS",
        new_value={"name": profile.name, "credential_type": profile.credential_type.value},
    )
    db.commit()
    return success(_to_out(db, profile))


@router.get("/credentials/{profile_id}", response_model=None)
def get_credential(profile_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("credential.view"))):
    profile = service.get_credential_profile(db, profile_id)
    return success(_to_out(db, profile))


@router.put("/credentials/{profile_id}", response_model=None)
def update_credential(
    profile_id: uuid.UUID,
    payload: CredentialProfileUpdate,
    db: DbSession,
    current_user=Depends(require_permission("credential.manage")),
):
    profile = service.update_credential_profile(
        db, profile_id, description=payload.description, username=payload.username, secrets=payload.secrets
    )
    rotated_keys = list(payload.secrets.keys()) if payload.secrets else []
    record_audit_event(
        db,
        user_id=current_user.id,
        action="CREDENTIAL_PROFILE_UPDATED",
        object_type="credential_profile",
        object_id=profile.id,
        result="SUCCESS",
        new_value={"rotated_secret_keys": rotated_keys},
    )
    db.commit()
    return success(_to_out(db, profile))
