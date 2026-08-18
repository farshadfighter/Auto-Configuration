"""Seeds default permissions, default roles (spec section 74), and a bootstrap Super
Administrator user. Idempotent - safe to run multiple times.

Usage:
    python -m app.db.seed
Environment overrides for the bootstrap admin:
    NGFABRIC_SEED_ADMIN_USERNAME (default: admin)
    NGFABRIC_SEED_ADMIN_EMAIL (default: admin@ngfabric.internal)
    NGFABRIC_SEED_ADMIN_PASSWORD (default: generated and printed once)
"""

import os
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models_registry import *  # noqa: F401,F403
from app.db.session import SessionLocal
from app.domains.identity.models import Permission, Role, User

# Permission catalog - resource.action per spec section 75. Extend as new domains land.
DEFAULT_PERMISSIONS: list[tuple[str, str]] = [
    ("user.view", "View users"),
    ("user.create", "Create users"),
    ("user.edit", "Edit users"),
    ("role.view", "View roles"),
    ("role.manage", "Create/edit roles and permission assignments"),
    ("asset.view", "View assets"),
    ("asset.create", "Create assets"),
    ("asset.edit", "Edit assets"),
    ("asset.delete", "Delete (soft-delete) assets"),
    ("credential.view", "View credential profile metadata (never secret values)"),
    ("credential.manage", "Create/rotate credential profiles"),
    ("audit.view", "View audit log"),
    ("settings.manage", "Manage system settings"),
    ("discovery.view", "View discovery jobs and results"),
    ("discovery.manage", "Create/cancel discovery jobs"),
    ("topology.view", "View topology graph and views"),
    ("topology.edit", "Create/edit topology nodes, links, and layouts"),
]

# Default roles - spec section 74. Super Administrator gets is_superuser bypass, not an
# explicit permission list.
DEFAULT_ROLES: dict[str, list[str]] = {
    "Super Administrator": [code for code, _ in DEFAULT_PERMISSIONS],
    "Administrator": [
        "user.view", "user.create", "user.edit", "role.view",
        "asset.view", "asset.create", "asset.edit", "asset.delete",
        "credential.view", "credential.manage", "audit.view", "settings.manage",
        "discovery.view", "discovery.manage", "topology.view", "topology.edit",
    ],
    "Network Architect": [
        "asset.view", "asset.create", "asset.edit", "credential.view", "audit.view",
        "discovery.view", "discovery.manage", "topology.view", "topology.edit",
    ],
    "Network Engineer": [
        "asset.view", "asset.edit", "credential.view",
        "discovery.view", "discovery.manage", "topology.view", "topology.edit",
    ],
    "Security Engineer": ["asset.view", "asset.edit", "credential.view", "audit.view", "topology.view"],
    "Microsoft Engineer": ["asset.view", "asset.edit", "credential.view", "discovery.view", "discovery.manage"],
    "Approver": ["asset.view", "audit.view"],
    "Operator": ["asset.view", "discovery.view", "topology.view"],
    "Auditor": ["audit.view", "asset.view"],
    "Viewer": ["asset.view", "discovery.view", "topology.view"],
}


def seed_permissions(db: Session) -> dict[str, Permission]:
    existing = {p.code: p for p in db.scalars(select(Permission))}
    for code, description in DEFAULT_PERMISSIONS:
        if code not in existing:
            permission = Permission(code=code, description=description)
            db.add(permission)
            existing[code] = permission
    db.flush()
    return existing


def seed_roles(db: Session, permissions: dict[str, Permission]) -> None:
    existing_roles = {r.name for r in db.scalars(select(Role))}
    for role_name, permission_codes in DEFAULT_ROLES.items():
        if role_name in existing_roles:
            continue
        role = Role(name=role_name, description=f"Default {role_name} role", is_system=True)
        role.permissions = [permissions[code] for code in permission_codes if code in permissions]
        db.add(role)
    db.flush()


def seed_bootstrap_admin(db: Session) -> None:
    username = os.environ.get("NGFABRIC_SEED_ADMIN_USERNAME", "admin")
    if db.scalar(select(User).where(User.username == username)):
        return
    email = os.environ.get("NGFABRIC_SEED_ADMIN_EMAIL", "admin@ngfabric.internal")
    password = os.environ.get("NGFABRIC_SEED_ADMIN_PASSWORD")
    generated = password is None
    if generated:
        password = secrets.token_urlsafe(18)
    user = User(
        username=username,
        email=email,
        full_name="NGFabric Administrator",
        hashed_password=hash_password(password),
        is_superuser=True,
    )
    db.add(user)
    db.flush()
    if generated:
        print(f"[seed] Bootstrap admin created: username={username} password={password}")
        print("[seed] Store this password now - it will not be shown again.")


def run() -> None:
    db = SessionLocal()
    try:
        permissions = seed_permissions(db)
        seed_roles(db, permissions)
        seed_bootstrap_admin(db)
        db.commit()
        print("[seed] Done.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
