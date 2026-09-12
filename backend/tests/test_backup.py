from tests.fakes import FakeDriver


def _create_asset(client, headers, asset_type, name, **extra):
    payload = {"name": name, "asset_type_id": str(asset_type.id), **extra}
    response = client.post("/api/v1/assets", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _create_reachable_asset(client, headers, asset_type, name):
    credential = client.post(
        "/api/v1/credentials",
        headers=headers,
        json={"name": f"{name}-cred", "credential_type": "username_password", "username": "admin", "secrets": {"password": "secret"}},
    ).json()["data"]
    return _create_asset(
        client, headers, asset_type, name, management_ip="10.4.4.4", credential_profile_id=credential["id"]
    )


def test_manual_backup_with_explicit_content(client, admin_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "bkp-switch-1")
    response = client.post(
        f"/api/v1/assets/{asset['id']}/backups",
        headers=admin_headers,
        json={"technology": "cisco_iosxe", "backup_type": "manual", "content": "hostname sw1\n"},
    )
    assert response.status_code == 201, response.text
    backup = response.json()["data"]
    assert len(backup["checksum"]) == 64
    assert backup["size_bytes"] == len("hostname sw1\n".encode())


def test_backup_list_and_detail(client, admin_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "bkp-switch-2")
    client.post(f"/api/v1/assets/{asset['id']}/backups", headers=admin_headers, json={"technology": "cisco_iosxe", "content": "a"})
    client.post(f"/api/v1/assets/{asset['id']}/backups", headers=admin_headers, json={"technology": "cisco_iosxe", "content": "b"})

    listing = client.get(f"/api/v1/assets/{asset['id']}/backups", headers=admin_headers).json()["data"]
    assert len(listing) == 2

    detail = client.get(f"/api/v1/backups/{listing[0]['id']}", headers=admin_headers).json()["data"]
    assert "content" in detail


def test_backup_compare(client, admin_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "bkp-switch-3")
    b1 = client.post(f"/api/v1/assets/{asset['id']}/backups", headers=admin_headers, json={"technology": "cisco_iosxe", "content": "vlan 10\n"}).json()["data"]
    b2 = client.post(f"/api/v1/assets/{asset['id']}/backups", headers=admin_headers, json={"technology": "cisco_iosxe", "content": "vlan 20\n"}).json()["data"]

    response = client.get("/api/v1/backups/compare", headers=admin_headers, params={"backup_a": b1["id"], "backup_b": b2["id"]})
    assert response.status_code == 200
    assert any("vlan 20" in line for line in response.json()["data"]["diff"])


def test_live_backup_requires_credential_profile(client, admin_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "bkp-no-cred")
    response = client.post(f"/api/v1/assets/{asset['id']}/backups", headers=admin_headers, json={"technology": "cisco_iosxe"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_CREDENTIAL_PROFILE"


def test_live_backup_with_fake_driver(client, admin_headers, asset_type, monkeypatch):
    asset = _create_reachable_asset(client, admin_headers, asset_type, "bkp-live")
    fake = FakeDriver()
    monkeypatch.setattr("app.domains.backup.service.get_driver", lambda tech: fake)

    response = client.post(f"/api/v1/assets/{asset['id']}/backups", headers=admin_headers, json={"technology": "cisco_iosxe"})
    assert response.status_code == 201, response.text
    detail = client.get(f"/api/v1/backups/{response.json()['data']['id']}", headers=admin_headers).json()["data"]
    assert detail["content"] == fake.backup_content
    assert fake.connected is False  # disconnected after use


def test_restore_with_fake_driver(client, admin_headers, asset_type, monkeypatch):
    asset = _create_reachable_asset(client, admin_headers, asset_type, "bkp-restore")
    backup = client.post(
        f"/api/v1/assets/{asset['id']}/backups", headers=admin_headers, json={"technology": "cisco_iosxe", "content": "hostname old\n"}
    ).json()["data"]

    fake = FakeDriver()
    monkeypatch.setattr("app.domains.backup.service.get_driver", lambda tech: fake)

    response = client.post(f"/api/v1/backups/{backup['id']}/restore", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["output"] == "rolled back"


def test_viewer_cannot_create_backup(client, admin_headers, viewer_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "bkp-denied")
    response = client.post(
        f"/api/v1/assets/{asset['id']}/backups", headers=viewer_headers, json={"technology": "cisco_iosxe", "content": "x"}
    )
    assert response.status_code == 403
