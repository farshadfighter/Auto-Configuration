def test_viewer_can_list_assets(client, viewer_headers):
    response = client.get("/api/v1/assets", headers=viewer_headers)
    assert response.status_code == 200


def test_viewer_cannot_create_asset(client, viewer_headers, asset_type):
    response = client.post(
        "/api/v1/assets",
        headers=viewer_headers,
        json={"name": "denied-asset", "asset_type_id": str(asset_type.id)},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_can_create_asset(client, admin_headers, asset_type):
    response = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={"name": "allowed-asset", "asset_type_id": str(asset_type.id)},
    )
    assert response.status_code == 201
