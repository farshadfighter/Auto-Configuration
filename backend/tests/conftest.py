import base64
import os

os.environ.setdefault("NGFABRIC_SECRET_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode())
os.environ.setdefault(
    "NGFABRIC_DATABASE_URL", "postgresql+psycopg://ngfabric:ngfabric@localhost:5432/ngfabric_test"
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.db.base import Base
from app.db.models_registry import *  # noqa: F401,F403 - populate Base.metadata
from app.db.seed import DEFAULT_PERMISSIONS, DEFAULT_ROLES
from app.domains.identity import service as identity_service
from app.domains.identity.models import Permission, Role
from app.main import app

TEST_DATABASE_URL = os.environ["NGFABRIC_DATABASE_URL"]
engine = create_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def _setup_schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as conn:
        table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seeded_permissions(db_session):
    permissions = {}
    for code, description in DEFAULT_PERMISSIONS:
        permission = Permission(code=code, description=description)
        db_session.add(permission)
        permissions[code] = permission
    db_session.flush()
    for role_name, codes in DEFAULT_ROLES.items():
        role = Role(name=role_name, is_system=True)
        role.permissions = [permissions[c] for c in codes if c in permissions]
        db_session.add(role)
    db_session.commit()
    return permissions


@pytest.fixture
def admin_user(db_session, seeded_permissions):
    user = identity_service.create_user(
        db_session, username="admin", email="admin@ngfabric.internal", password="AdminPass123!"
    )
    user.is_superuser = True
    db_session.commit()
    return user


@pytest.fixture
def viewer_user(db_session, seeded_permissions):
    role = db_session.query(Role).filter_by(name="Viewer").one()
    user = identity_service.create_user(
        db_session,
        username="viewer1",
        email="viewer1@ngfabric.internal",
        password="ViewerPass123!",
        role_ids=[role.id],
    )
    db_session.commit()
    return user


def auth_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client, admin_user):
    return auth_headers(client, "admin", "AdminPass123!")


@pytest.fixture
def viewer_headers(client, viewer_user):
    return auth_headers(client, "viewer1", "ViewerPass123!")


@pytest.fixture
def asset_type(db_session):
    from app.domains.assets.models import AssetType

    asset_type = AssetType(code="router", name="Router")
    db_session.add(asset_type)
    db_session.commit()
    return asset_type
