def test_create_and_get_asset(client, admin_headers, asset_type):
    create = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={
            "name": "core-sw-01",
            "hostname": "core-sw-01.lab",
            "asset_type_id": str(asset_type.id),
            "management_ip": "10.0.0.1",
            "mac_address": "00:11:22:33:44:55",
            "criticality": "high",
            "status": "active",
            "managed": "managed",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()["data"]
    assert body["asset_code"].startswith("AST-")
    assert body["management_ip"] == "10.0.0.1"
    assert body["mac_address"] == "00:11:22:33:44:55"

    get_response = client.get(f"/api/v1/assets/{body['id']}", headers=admin_headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["name"] == "core-sw-01"


def test_get_nonexistent_asset_returns_404(client, admin_headers):
    response = client.get("/api/v1/assets/00000000-0000-0000-0000-000000000000", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ASSET_NOT_FOUND"


def test_duplicate_by_management_ip_is_rejected(client, admin_headers, asset_type):
    first = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={"name": "sw-a", "asset_type_id": str(asset_type.id), "management_ip": "10.0.0.5"},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={"name": "sw-b", "asset_type_id": str(asset_type.id), "management_ip": "10.0.0.5"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DUPLICATE_ASSET"


def test_duplicate_by_hostname_is_rejected(client, admin_headers, asset_type):
    first = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={"name": "sw-a", "hostname": "shared.lab", "asset_type_id": str(asset_type.id)},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={"name": "sw-b", "hostname": "shared.lab", "asset_type_id": str(asset_type.id)},
    )
    assert second.status_code == 409


def test_update_asset(client, admin_headers, asset_type):
    create = client.post(
        "/api/v1/assets", headers=admin_headers, json={"name": "sw-1", "asset_type_id": str(asset_type.id)}
    )
    asset_id = create.json()["data"]["id"]

    update = client.put(
        f"/api/v1/assets/{asset_id}", headers=admin_headers, json={"criticality": "critical", "status": "active"}
    )
    assert update.status_code == 200
    assert update.json()["data"]["criticality"] == "critical"
    assert update.json()["data"]["status"] == "active"


def test_soft_delete_excludes_from_list(client, admin_headers, asset_type):
    create = client.post(
        "/api/v1/assets", headers=admin_headers, json={"name": "sw-del", "asset_type_id": str(asset_type.id)}
    )
    asset_id = create.json()["data"]["id"]

    delete = client.delete(f"/api/v1/assets/{asset_id}", headers=admin_headers)
    assert delete.status_code == 204

    get_after_delete = client.get(f"/api/v1/assets/{asset_id}", headers=admin_headers)
    assert get_after_delete.status_code == 404

    listing = client.get("/api/v1/assets", headers=admin_headers)
    assert all(a["id"] != asset_id for a in listing.json()["data"])


def test_asset_relationships(client, admin_headers, asset_type):
    a = client.post(
        "/api/v1/assets", headers=admin_headers, json={"name": "core", "asset_type_id": str(asset_type.id)}
    ).json()["data"]
    b = client.post(
        "/api/v1/assets", headers=admin_headers, json={"name": "edge", "asset_type_id": str(asset_type.id)}
    ).json()["data"]

    rel = client.post(
        "/api/v1/assets/relationships",
        headers=admin_headers,
        json={"source_asset_id": a["id"], "target_asset_id": b["id"], "relationship_type": "connected_to"},
    )
    assert rel.status_code == 201

    listing = client.get(f"/api/v1/assets/{a['id']}/relationships", headers=admin_headers)
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1
    assert listing.json()["data"][0]["relationship_type"] == "connected_to"
