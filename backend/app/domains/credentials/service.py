import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.security import decrypt_secret, encrypt_secret
from app.domains.credentials.models import CredentialProfile, CredentialSecretRef


def create_credential_profile(
    db: Session, *, name: str, description: str | None, credential_type: str, username: str | None, secrets: dict[str, str]
) -> CredentialProfile:
    profile = CredentialProfile(name=name, description=description, credential_type=credential_type, username=username)
    db.add(profile)
    db.flush()
    for key, value in secrets.items():
        db.add(
            CredentialSecretRef(
                credential_profile_id=profile.id, secret_key=key, encrypted_value=encrypt_secret(value)
            )
        )
    db.flush()
    return profile


def get_credential_profile(db: Session, profile_id: uuid.UUID) -> CredentialProfile:
    profile = db.get(CredentialProfile, profile_id)
    if not profile:
        raise NotFoundError("CREDENTIAL_PROFILE_NOT_FOUND", f"Credential profile {profile_id} not found")
    return profile


def list_credential_profiles(db: Session) -> list[CredentialProfile]:
    return list(db.scalars(select(CredentialProfile)))


def get_secret_keys(db: Session, profile_id: uuid.UUID) -> list[str]:
    return list(
        db.scalars(select(CredentialSecretRef.secret_key).where(CredentialSecretRef.credential_profile_id == profile_id))
    )


def update_credential_profile(
    db: Session, profile_id: uuid.UUID, *, description: str | None, username: str | None, secrets: dict[str, str] | None
) -> CredentialProfile:
    profile = get_credential_profile(db, profile_id)
    if description is not None:
        profile.description = description
    if username is not None:
        profile.username = username
    if secrets:
        existing = {
            ref.secret_key: ref
            for ref in db.scalars(
                select(CredentialSecretRef).where(CredentialSecretRef.credential_profile_id == profile_id)
            )
        }
        for key, value in secrets.items():
            encrypted = encrypt_secret(value)
            if key in existing:
                existing[key].encrypted_value = encrypted
            else:
                db.add(CredentialSecretRef(credential_profile_id=profile_id, secret_key=key, encrypted_value=encrypted))
    db.flush()
    return profile


def resolve_secret(db: Session, profile_id: uuid.UUID, secret_key: str) -> str:
    """Decrypts a single secret. Intended for internal use by drivers/workers only - never
    call this from an API handler that returns the result to a client."""
    ref = db.scalar(
        select(CredentialSecretRef).where(
            CredentialSecretRef.credential_profile_id == profile_id, CredentialSecretRef.secret_key == secret_key
        )
    )
    if not ref:
        raise NotFoundError(
            "CREDENTIAL_SECRET_NOT_FOUND", f"Secret '{secret_key}' not found for credential profile {profile_id}"
        )
    return decrypt_secret(ref.encrypted_value)
