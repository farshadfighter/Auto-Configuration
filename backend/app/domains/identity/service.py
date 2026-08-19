import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import LockedError
from app.core.security import hash_password, verify_password
from app.domains.identity.models import Permission, Role, User

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if not user or not user.is_active or not user.hashed_password:
        return None
    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        raise LockedError(
            "ACCOUNT_LOCKED",
            "Account is temporarily locked due to repeated failed login attempts. Try again later.",
        )
    if not verify_password(password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + LOCKOUT_DURATION
        return None
    user.failed_login_attempts = 0
    user.locked_until = None
    return user


def create_user(
    db: Session, username: str, email: str, password: str, full_name: str | None = None, role_ids: list[uuid.UUID] | None = None
) -> User:
    user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
    )
    if role_ids:
        user.roles = list(db.scalars(select(Role).where(Role.id.in_(role_ids))))
    db.add(user)
    db.flush()
    return user


def get_effective_permissions(user: User) -> set[str]:
    """Union of permissions granted directly via roles and indirectly via group roles."""
    codes: set[str] = set()
    for role in user.roles:
        codes.update(p.code for p in role.permissions)
    for group in user.groups:
        for role in group.roles:
            codes.update(p.code for p in role.permissions)
    return codes


def user_has_permission(user: User, code: str) -> bool:
    if user.is_superuser:
        return True
    return code in get_effective_permissions(user)


def create_role(db: Session, name: str, description: str | None, permission_codes: list[str]) -> Role:
    role = Role(name=name, description=description)
    if permission_codes:
        role.permissions = list(db.scalars(select(Permission).where(Permission.code.in_(permission_codes))))
    db.add(role)
    db.flush()
    return role
