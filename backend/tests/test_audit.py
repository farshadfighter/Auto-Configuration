def test_login_creates_audit_event(client, admin_user, admin_headers):
    response = client.get("/api/v1/audit/events?object_type=user", headers=admin_headers)
    assert response.status_code == 200
    actions = [e["action"] for e in response.json()["data"]]
    assert "LOGIN_SUCCESS" in actions


def test_asset_creation_creates_audit_event(client, admin_headers, asset_type):
    create = client.post(
        "/api/v1/assets", headers=admin_headers, json={"name": "audited-asset", "asset_type_id": str(asset_type.id)}
    )
    asset_id = create.json()["data"]["id"]

    response = client.get(f"/api/v1/audit/events?object_type=asset&object_id={asset_id}", headers=admin_headers)
    assert response.status_code == 200
    events = response.json()["data"]
    assert len(events) == 1
    assert events[0]["action"] == "ASSET_CREATED"


def test_failed_login_is_audited(client, admin_user, admin_headers):
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong-password"})
    response = client.get("/api/v1/audit/events?object_type=user", headers=admin_headers)
    actions = [e["action"] for e in response.json()["data"]]
    assert "LOGIN_FAILED" in actions
