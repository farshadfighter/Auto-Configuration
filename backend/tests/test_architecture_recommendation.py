def _create_asset(client, headers, asset_type, name, safe_pin=None, **extra):
    payload = {"name": name, "asset_type_id": str(asset_type.id), **extra}
    if safe_pin:
        payload["safe_pin"] = safe_pin
    response = client.post("/api/v1/assets", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_generate_safe_recommendation_reflects_classified_inventory(client, admin_headers, asset_type):
    # asset_type fixture is a "router" type per conftest.
    _create_asset(client, admin_headers, asset_type, "edge-rtr-01", safe_pin="internet_edge")
    # Unclassified asset - must not appear anywhere in the generated design.
    _create_asset(client, admin_headers, asset_type, "unclassified-switch")

    response = client.post(
        "/api/v1/architecture-recommendations/safe", headers=admin_headers, json={"name": "SAFE Recommendation Test"}
    )
    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["name"] == "SAFE Recommendation Test"

    graph = client.get(f"/api/v1/designs/versions/{body['version_id']}", headers=admin_headers).json()["data"]
    components = graph["components"]
    assert len(components) > 0

    # The classified router shows up as a real (non-recommended) component in its PIN.
    real_components = [c for c in components if not c["properties"]["recommended"]]
    assert any(c["name"] == "edge-rtr-01" and c["properties"]["safe_pin"] == "internet_edge" for c in real_components)

    # The unclassified asset must not appear anywhere in the generated design.
    assert not any(c["name"] == "unclassified-switch" for c in components)

    # Every PIN's recommended-but-unmet roles show up as recommended (dashed) components -
    # e.g. internet_edge still needs a firewall/IPS/VPN concentrator even though it has a router.
    recommended_components = [c for c in components if c["properties"]["recommended"]]
    assert any(c["properties"]["safe_pin"] == "internet_edge" for c in recommended_components)

    # Relationships connect PINs together (e.g. internet_edge -> campus_core per the reference
    # topology), not just isolated nodes.
    assert len(graph["relationships"]) > 0


def test_safe_recommendation_marks_firewall_asset_type_as_satisfying_perimeter_firewall(client, admin_headers, asset_type, db_session):
    from app.domains.assets.models import AssetType

    firewall_type = AssetType(code="firewall", name="Firewall")
    db_session.add(firewall_type)
    db_session.commit()

    _create_asset(client, admin_headers, asset_type, "edge-rtr-02", safe_pin="internet_edge")
    _create_asset(
        client,
        admin_headers,
        asset_type,
        "edge-fw-01",
        safe_pin="internet_edge",
        asset_type_id=str(firewall_type.id),
    )

    response = client.post(
        "/api/v1/architecture-recommendations/safe", headers=admin_headers, json={"name": "SAFE FW Test"}
    )
    version_id = response.json()["data"]["version_id"]
    graph = client.get(f"/api/v1/designs/versions/{version_id}", headers=admin_headers).json()["data"]

    edge_components = [c for c in graph["components"] if c["properties"]["safe_pin"] == "internet_edge"]
    recommended_names = {c["name"] for c in edge_components if c["properties"]["recommended"]}
    # A firewall asset already exists in this PIN, so "Perimeter Firewall (NGFW)" must NOT
    # also show up as a recommended/missing component.
    assert "Perimeter Firewall (NGFW)" not in recommended_names


def test_viewer_cannot_generate_safe_recommendation(client, viewer_headers):
    response = client.post(
        "/api/v1/architecture-recommendations/safe", headers=viewer_headers, json={"name": "Denied"}
    )
    assert response.status_code == 403
