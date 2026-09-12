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
from app.domains.assets.models import AssetType, ComplianceFramework
from app.domains.identity.models import Permission, Role, User

# Baseline asset type catalog - without at least these, neither manual asset creation nor
# CSV discovery import (which resolves asset_type_code -> AssetType) has anything to point
# at in a freshly-seeded database.
DEFAULT_ASSET_TYPES: list[tuple[str, str, str]] = [
    ("router", "Router", "network"),
    ("switch", "Switch", "network"),
    ("firewall", "Firewall", "network"),
    ("load_balancer", "Load Balancer", "network"),
    ("server", "Server", "compute"),
    ("domain_controller", "Domain Controller", "microsoft"),
    ("dns_server", "DNS Server", "microsoft"),
    ("dhcp_server", "DHCP Server", "microsoft"),
]

# Controlled compliance-framework catalog for the ISMS asset register's compliance_scope -
# deliberately not free text (see app.domains.assets.models.ComplianceFramework).
DEFAULT_COMPLIANCE_FRAMEWORKS: list[tuple[str, str]] = [
    ("iso27001", "ISO/IEC 27001"),
    ("pci_dss", "PCI-DSS"),
    ("gdpr", "GDPR"),
    ("hipaa", "HIPAA"),
    ("soc2", "SOC 2"),
    ("nist_csf", "NIST Cybersecurity Framework"),
]

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
    ("best_practice.view", "View architecture findings"),
    ("best_practice.run", "Trigger a best-practice analysis run"),
    ("best_practice.triage", "Accept or ignore architecture findings"),
    ("design.view", "View architecture designs"),
    ("design.create", "Create architecture designs"),
    ("design.edit", "Edit design components/relationships and create new versions"),
    ("design.approve", "Approve an architecture design version"),
    ("configuration.view", "View configuration jobs, objects, profiles, and the technology catalog"),
    ("configuration.create", "Create configuration jobs/objects/profiles"),
    ("configuration.generate", "Generate a configuration job's plan"),
    ("configuration.validate", "Validate a configuration job"),
    ("approval.view", "View approval requests"),
    ("approval.approve", "Approve or reject a configuration job"),
    ("backup.view", "View backups"),
    ("backup.create", "Create a backup (manual or from a live device)"),
    ("backup.restore", "Restore a backup to a live device"),
    ("deployment.view", "View deployment jobs, events, and results"),
    ("deployment.execute", "Create and start deployment jobs"),
    ("drift.view", "View configuration drift findings"),
    ("drift.run", "Trigger a drift analysis run"),
    ("drift.triage", "Accept, ignore, or remediate a drift finding"),
    ("reports.view", "View reports"),
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
        "best_practice.view", "best_practice.run", "best_practice.triage",
        "design.view", "design.create", "design.edit", "design.approve",
        "configuration.view", "configuration.create", "configuration.generate", "configuration.validate",
        "approval.view", "approval.approve", "backup.view", "backup.create", "backup.restore",
        "deployment.view", "deployment.execute", "drift.view", "drift.run", "drift.triage", "reports.view",
    ],
    "Network Architect": [
        "asset.view", "asset.create", "asset.edit", "credential.view", "audit.view",
        "discovery.view", "discovery.manage", "topology.view", "topology.edit",
        "best_practice.view", "best_practice.run", "best_practice.triage",
        "design.view", "design.create", "design.edit", "design.approve",
        "configuration.view", "configuration.create", "configuration.generate", "configuration.validate",
        "approval.view", "approval.approve", "backup.view", "backup.create", "backup.restore",
        "deployment.view", "deployment.execute", "drift.view", "drift.run", "drift.triage", "reports.view",
    ],
    "Network Engineer": [
        "asset.view", "asset.edit", "credential.view",
        "discovery.view", "discovery.manage", "topology.view", "topology.edit",
        "best_practice.view", "best_practice.run",
        "design.view", "design.create", "design.edit",
        "configuration.view", "configuration.create", "configuration.generate", "configuration.validate",
        "backup.view", "backup.create", "deployment.view", "deployment.execute",
        "drift.view", "drift.run", "drift.triage", "reports.view",
    ],
    "Security Engineer": [
        "asset.view", "asset.edit", "credential.view", "audit.view", "topology.view",
        "best_practice.view", "best_practice.run", "best_practice.triage",
        "design.view", "configuration.view", "approval.view", "approval.approve", "backup.view",
        "drift.view", "reports.view",
    ],
    "Microsoft Engineer": [
        "asset.view", "asset.edit", "credential.view", "discovery.view", "discovery.manage",
        "best_practice.view", "best_practice.run",
        "design.view", "design.create", "design.edit",
        "configuration.view", "configuration.create", "configuration.generate", "configuration.validate",
        "backup.view", "backup.create", "deployment.view", "deployment.execute",
        "drift.view", "drift.run", "drift.triage", "reports.view",
    ],
    "Approver": [
        "asset.view", "audit.view", "best_practice.view", "design.view", "design.approve", "configuration.view",
        "approval.view", "approval.approve", "reports.view",
    ],
    "Operator": [
        "asset.view", "discovery.view", "topology.view", "best_practice.view", "design.view", "configuration.view",
        "backup.view", "deployment.view", "drift.view", "reports.view",
    ],
    "Auditor": [
        "audit.view", "asset.view", "best_practice.view", "design.view", "configuration.view",
        "approval.view", "backup.view", "deployment.view", "drift.view", "reports.view",
    ],
    "Viewer": [
        "asset.view", "discovery.view", "topology.view", "best_practice.view", "design.view", "configuration.view",
        "backup.view", "deployment.view", "drift.view", "reports.view",
    ],
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


def seed_asset_types(db: Session) -> None:
    existing = {t.code for t in db.scalars(select(AssetType))}
    for code, name, category in DEFAULT_ASSET_TYPES:
        if code not in existing:
            db.add(AssetType(code=code, name=name, category=category))
    db.flush()


def seed_compliance_frameworks(db: Session) -> None:
    existing = {f.code for f in db.scalars(select(ComplianceFramework))}
    for code, name in DEFAULT_COMPLIANCE_FRAMEWORKS:
        if code not in existing:
            db.add(ComplianceFramework(code=code, name=name))
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
        seed_asset_types(db)
        seed_compliance_frameworks(db)
        seed_bootstrap_admin(db)
        db.commit()
        print("[seed] Done.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
