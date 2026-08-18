def test_login_success(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "AdminPass123!"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_login_unknown_user(client):
    response = client.post("/api/v1/auth/login", json={"username": "ghost", "password": "whatever"})
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, admin_headers):
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "admin"


def test_refresh_token_issues_new_access_token(client, admin_user):
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "AdminPass123!"})
    refresh_token = login.json()["data"]["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


def test_access_token_rejected_on_refresh_endpoint(client, admin_user):
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "AdminPass123!"})
    access_token = login.json()["data"]["access_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401
