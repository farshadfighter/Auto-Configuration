def test_create_design_creates_initial_version(client, admin_headers):
    response = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Branch Standard", "mode": "manual"})
    assert response.status_code == 201, response.text
    design = response.json()["data"]

    detail = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]
    assert detail["latest_version"]["version_number"] == 1
    assert detail["latest_version"]["status"] == "draft"
    assert detail["latest_version"]["version_label"] == "v1.0"


def test_add_components_and_relationship(client, admin_headers):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Core Design"}).json()["data"]
    version_id = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]["latest_version"]["id"]

    core = client.post(
        f"/api/v1/designs/versions/{version_id}/components",
        headers=admin_headers,
        json={"component_type": "router", "name": "Core-1"},
    ).json()["data"]
    edge = client.post(
        f"/api/v1/designs/versions/{version_id}/components",
        headers=admin_headers,
        json={"component_type": "switch", "name": "Edge-1"},
    ).json()["data"]

    rel = client.post(
        f"/api/v1/designs/versions/{version_id}/relationships",
        headers=admin_headers,
        json={"source_component_id": core["id"], "target_component_id": edge["id"], "relationship_type": "uplink"},
    )
    assert rel.status_code == 201

    graph = client.get(f"/api/v1/designs/versions/{version_id}", headers=admin_headers).json()["data"]
    assert len(graph["components"]) == 2
    assert len(graph["relationships"]) == 1


def test_relationship_persists_source_and_target_interface(client, admin_headers):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Port Test"}).json()["data"]
    version_id = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]["latest_version"]["id"]

    core = client.post(
        f"/api/v1/designs/versions/{version_id}/components",
        headers=admin_headers,
        json={"component_type": "router", "name": "Core-1"},
    ).json()["data"]
    edge = client.post(
        f"/api/v1/designs/versions/{version_id}/components",
        headers=admin_headers,
        json={"component_type": "switch", "name": "Edge-1"},
    ).json()["data"]

    rel = client.post(
        f"/api/v1/designs/versions/{version_id}/relationships",
        headers=admin_headers,
        json={
            "source_component_id": core["id"],
            "target_component_id": edge["id"],
            "relationship_type": "uplink",
            "source_interface": "Gi0/1",
            "target_interface": "Gi0/24",
        },
    )
    assert rel.status_code == 201, rel.text
    assert rel.json()["data"]["source_interface"] == "Gi0/1"
    assert rel.json()["data"]["target_interface"] == "Gi0/24"

    graph = client.get(f"/api/v1/designs/versions/{version_id}", headers=admin_headers).json()["data"]
    relationship = graph["relationships"][0]
    assert relationship["source_interface"] == "Gi0/1"
    assert relationship["target_interface"] == "Gi0/24"


def test_new_version_clones_relationship_interfaces(client, admin_headers):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Clone Interface Test"}).json()["data"]
    v1_id = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]["latest_version"]["id"]
    core = client.post(
        f"/api/v1/designs/versions/{v1_id}/components",
        headers=admin_headers,
        json={"component_type": "router", "name": "Core-1"},
    ).json()["data"]
    edge = client.post(
        f"/api/v1/designs/versions/{v1_id}/components",
        headers=admin_headers,
        json={"component_type": "switch", "name": "Edge-1"},
    ).json()["data"]
    client.post(
        f"/api/v1/designs/versions/{v1_id}/relationships",
        headers=admin_headers,
        json={
            "source_component_id": core["id"],
            "target_component_id": edge["id"],
            "relationship_type": "uplink",
            "source_interface": "Gi0/1",
            "target_interface": "Gi0/24",
        },
    )
    client.post(f"/api/v1/designs/{design['id']}/approve", headers=admin_headers, json={})
    v2 = client.post(f"/api/v1/designs/{design['id']}/versions", headers=admin_headers).json()["data"]

    graph = client.get(f"/api/v1/designs/versions/{v2['id']}", headers=admin_headers).json()["data"]
    assert len(graph["relationships"]) == 1
    cloned = graph["relationships"][0]
    assert cloned["source_interface"] == "Gi0/1"
    assert cloned["target_interface"] == "Gi0/24"


def test_approve_design_and_edit_requires_new_version(client, admin_headers):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "To Approve"}).json()["data"]
    version_id = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]["latest_version"]["id"]

    approve = client.post(f"/api/v1/designs/{design['id']}/approve", headers=admin_headers, json={"comment": "Looks good"})
    assert approve.status_code == 200
    assert approve.json()["data"]["status"] == "approved"

    blocked = client.post(
        f"/api/v1/designs/versions/{version_id}/components",
        headers=admin_headers,
        json={"component_type": "router", "name": "Blocked"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "DESIGN_VERSION_NOT_EDITABLE"

    new_version = client.post(f"/api/v1/designs/{design['id']}/versions", headers=admin_headers)
    assert new_version.status_code == 201
    assert new_version.json()["data"]["version_number"] == 2
    assert new_version.json()["data"]["status"] == "draft"


def test_new_version_clones_components(client, admin_headers):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Clone Test"}).json()["data"]
    v1_id = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]["latest_version"]["id"]
    client.post(
        f"/api/v1/designs/versions/{v1_id}/components",
        headers=admin_headers,
        json={"component_type": "router", "name": "Core-1"},
    )
    client.post(f"/api/v1/designs/{design['id']}/approve", headers=admin_headers, json={})
    v2 = client.post(f"/api/v1/designs/{design['id']}/versions", headers=admin_headers).json()["data"]

    graph = client.get(f"/api/v1/designs/versions/{v2['id']}", headers=admin_headers).json()["data"]
    assert len(graph["components"]) == 1
    assert graph["components"][0]["name"] == "Core-1"


def test_approving_new_version_supersedes_previous(client, admin_headers):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Supersede Test"}).json()["data"]
    v1 = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]["latest_version"]
    client.post(f"/api/v1/designs/{design['id']}/approve", headers=admin_headers, json={})
    v2 = client.post(f"/api/v1/designs/{design['id']}/versions", headers=admin_headers).json()["data"]
    client.post(f"/api/v1/designs/{design['id']}/approve", headers=admin_headers, json={})

    v1_graph_check = client.get(f"/api/v1/designs/versions/{v1['id']}", headers=admin_headers)
    assert v1_graph_check.status_code == 200  # version itself still readable/auditable

    detail = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]
    assert detail["latest_version"]["id"] == v2["id"]
    assert detail["latest_version"]["status"] == "approved"


def test_map_component_to_asset(client, admin_headers, asset_type):
    asset = client.post(
        "/api/v1/assets", headers=admin_headers, json={"name": "mapped-asset", "asset_type_id": str(asset_type.id)}
    ).json()["data"]
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Mapping Test"}).json()["data"]
    version_id = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]["latest_version"]["id"]
    component = client.post(
        f"/api/v1/designs/versions/{version_id}/components",
        headers=admin_headers,
        json={"component_type": "router", "name": "Core-1"},
    ).json()["data"]

    response = client.post(
        f"/api/v1/designs/components/{component['id']}/map-asset", headers=admin_headers, json={"asset_id": asset["id"]}
    )
    assert response.status_code == 200

    # The graph response must surface the mapped asset_id so the frontend can build a
    # "Configure this device" / "View Asset" deep link per node.
    graph = client.get(f"/api/v1/designs/versions/{version_id}", headers=admin_headers).json()["data"]
    mapped = next(c for c in graph["components"] if c["id"] == component["id"])
    assert mapped["asset_id"] == asset["id"]

    unmapped_component = client.post(
        f"/api/v1/designs/versions/{version_id}/components",
        headers=admin_headers,
        json={"component_type": "switch", "name": "Access-1"},
    ).json()["data"]
    graph = client.get(f"/api/v1/designs/versions/{version_id}", headers=admin_headers).json()["data"]
    unmapped = next(c for c in graph["components"] if c["id"] == unmapped_component["id"])
    assert unmapped["asset_id"] is None


def test_map_component_to_unknown_asset_returns_404_not_a_crash(client, admin_headers):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Bad Asset Mapping"}).json()["data"]
    version_id = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]["latest_version"]["id"]
    component = client.post(
        f"/api/v1/designs/versions/{version_id}/components",
        headers=admin_headers,
        json={"component_type": "router", "name": "Core-2"},
    ).json()["data"]

    response = client.post(
        f"/api/v1/designs/components/{component['id']}/map-asset",
        headers=admin_headers,
        json={"asset_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ASSET_NOT_FOUND"


def test_map_unknown_recommendation_returns_404_not_a_crash(client, admin_headers):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Bad Finding Mapping"}).json()["data"]
    version_id = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]["latest_version"]["id"]

    response = client.post(
        f"/api/v1/designs/versions/{version_id}/map-recommendation",
        headers=admin_headers,
        json={"finding_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FINDING_NOT_FOUND"


def test_viewer_cannot_create_design(client, viewer_headers):
    response = client.post("/api/v1/designs", headers=viewer_headers, json={"name": "denied"})
    assert response.status_code == 403
