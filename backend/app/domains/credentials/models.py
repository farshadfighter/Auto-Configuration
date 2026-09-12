import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class CredentialType(str, enum.Enum):
    USERNAME_PASSWORD = "username_password"
    SSH_KEY = "ssh_key"
    ENABLE_PASSWORD = "enable_password"
    API_TOKEN = "api_token"
    API_KEY = "api_key"
    WINRM = "winrm"
    CERTIFICATE = "certificate"
    SECRET = "secret"


class CredentialProfile(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "credential_profiles"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    credential_type: Mapped[CredentialType] = mapped_column(
        Enum(CredentialType, name="credential_type", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)


class CredentialSecretRef(UUIDPKMixin, TimestampMixin, Base):
    """Stores an encrypted secret value scoped to a credential profile.

    The database only ever holds ciphertext (AES-256-GCM, app.core.security). Decrypted
    values must never be logged, returned by the API, or rendered in the UI.
    """

    __tablename__ = "credential_secret_refs"

    credential_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credential_profiles.id", ondelete="CASCADE"), nullable=False
    )
    secret_key: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "password", "ssh_private_key"
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("credential_profile_id", "secret_key", name="uq_credential_secret_key"),)
