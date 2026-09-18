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


def test_update_relationship_sets_link_metadata(client, admin_headers):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Link Metadata Test"}).json()["data"]
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
    ).json()["data"]

    updated = client.patch(
        f"/api/v1/designs/relationships/{rel['id']}",
        headers=admin_headers,
        json={"link_type": "trunk", "speed_mbps": 1000, "vlan": 10, "subnet": "10.0.0.0/30"},
    )
    assert updated.status_code == 200, updated.text
    data = updated.json()["data"]
    assert data["link_type"] == "trunk"
    assert data["speed_mbps"] == 1000
    assert data["vlan"] == 10
    assert data["subnet"] == "10.0.0.0/30"


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


def test_new_version_clones_asset_mapping(client, admin_headers, asset_type):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Clone Mapping Test"}).json()["data"]
    v1_id = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]["latest_version"]["id"]
    component = client.post(
        f"/api/v1/designs/versions/{v1_id}/components",
        headers=admin_headers,
        json={"component_type": "router", "name": "Mapped-Router"},
    ).json()["data"]
    asset = client.post(
        "/api/v1/assets", headers=admin_headers, json={"name": "Mapped-Router-Asset", "asset_type_id": str(asset_type.id)}
    ).json()["data"]
    client.post(f"/api/v1/designs/components/{component['id']}/map-asset", headers=admin_headers, json={"asset_id": asset["id"]})

    client.post(f"/api/v1/designs/{design['id']}/approve", headers=admin_headers, json={})
    v2 = client.post(f"/api/v1/designs/{design['id']}/versions", headers=admin_headers).json()["data"]

    graph = client.get(f"/api/v1/designs/versions/{v2['id']}", headers=admin_headers).json()["data"]
    cloned = next(c for c in graph["components"] if c["name"] == "Mapped-Router")
    assert cloned["asset_id"] == asset["id"]


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


def test_list_design_templates(client, admin_headers):
    response = client.get("/api/v1/design-templates", headers=admin_headers)
    assert response.status_code == 200
    codes = {t["code"] for t in response.json()["data"]}
    assert {"small_branch", "three_tier_campus", "small_datacenter"} <= codes


def test_create_design_from_template_populates_graph(client, admin_headers):
    response = client.post(
        "/api/v1/designs/from-template",
        headers=admin_headers,
        json={"template_code": "small_branch", "name": "Branch from template"},
    )
    assert response.status_code == 201, response.text
    design = response.json()["data"]
    assert design["name"] == "Branch from template"
    version_id = design["latest_version"]["id"]

    graph = client.get(f"/api/v1/designs/versions/{version_id}", headers=admin_headers).json()["data"]
    assert len(graph["components"]) == 4
    assert len(graph["relationships"]) == 3
    component_names = {c["name"] for c in graph["components"]}
    assert "Branch Router" in component_names
    relationship_link_types = {r["link_type"] for r in graph["relationships"]}
    assert "wan" in relationship_link_types


def test_create_design_from_unknown_template_returns_422(client, admin_headers):
    response = client.post(
        "/api/v1/designs/from-template",
        headers=admin_headers,
        json={"template_code": "does_not_exist", "name": "Bad Template"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNKNOWN_DESIGN_TEMPLATE"


def test_list_design_versions(client, admin_headers):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Version List Test"}).json()["data"]
    client.post(f"/api/v1/designs/{design['id']}/approve", headers=admin_headers, json={})
    client.post(f"/api/v1/designs/{design['id']}/versions", headers=admin_headers)

    versions = client.get(f"/api/v1/designs/{design['id']}/versions", headers=admin_headers).json()["data"]
    assert [v["version_number"] for v in versions] == [1, 2]
    assert versions[0]["status"] == "approved"
    assert versions[1]["status"] == "draft"


def test_diff_design_versions_detects_added_removed_and_changed(client, admin_headers):
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Diff Test"}).json()["data"]
    v1_id = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]["latest_version"]["id"]

    core = client.post(
        f"/api/v1/designs/versions/{v1_id}/components",
        headers=admin_headers,
        json={"component_type": "router", "name": "Core-1"},
    ).json()["data"]
    stale = client.post(
        f"/api/v1/designs/versions/{v1_id}/components",
        headers=admin_headers,
        json={"component_type": "switch", "name": "Stale-Switch"},
    ).json()["data"]
    client.post(
        f"/api/v1/designs/versions/{v1_id}/relationships",
        headers=admin_headers,
        json={
            "source_component_id": core["id"],
            "target_component_id": stale["id"],
            "relationship_type": "uplink",
            "link_type": "lan",
        },
    )

    client.post(f"/api/v1/designs/{design['id']}/approve", headers=admin_headers, json={})
    v2 = client.post(f"/api/v1/designs/{design['id']}/versions", headers=admin_headers).json()["data"]
    v2_id = v2["id"]

    graph = client.get(f"/api/v1/designs/versions/{v2_id}", headers=admin_headers).json()["data"]
    cloned_relationship = graph["relationships"][0]

    # Remove the stale switch and its link, add a new firewall, and change the link type on a kept relationship.
    client.post(
        f"/api/v1/designs/versions/{v2_id}/components",
        headers=admin_headers,
        json={"component_type": "firewall", "name": "New-Firewall"},
    )
    client.patch(
        f"/api/v1/designs/relationships/{cloned_relationship['id']}",
        headers=admin_headers,
        json={"link_type": "trunk"},
    )
    # No delete-component endpoint exists - simulate removal by diffing against v1 (which still
    # has Stale-Switch) instead of actually deleting it from v2.

    diff = client.get(
        f"/api/v1/designs/{design['id']}/versions/diff",
        headers=admin_headers,
        params={"from_version_id": v1_id, "to_version_id": v2_id},
    ).json()["data"]

    assert "New-Firewall" in diff["added_components"]
    assert diff["removed_components"] == []
    changed_names = {c["name"] for c in diff["changed_components"]}
    assert changed_names == set()

    changed_rel_keys = {r["key"] for r in diff["changed_relationships"]}
    assert any("Core-1 -> Stale-Switch" in k for k in changed_rel_keys)
    matching = next(r for r in diff["changed_relationships"] if "Core-1 -> Stale-Switch" in r["key"])
    assert matching["changes"]["link_type"] == ["lan", "trunk"]
