def _create_asset(client, headers, asset_type, name, **extra):
    payload = {"name": name, "asset_type_id": str(asset_type.id), **extra}
    response = client.post("/api/v1/assets", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_topology_sync_derives_nodes_and_links(client, admin_headers, asset_type):
    core = _create_asset(client, admin_headers, asset_type, "topo-core")
    edge = _create_asset(client, admin_headers, asset_type, "topo-edge")
    rel = client.post(
        "/api/v1/assets/relationships",
        headers=admin_headers,
        json={"source_asset_id": core["id"], "target_asset_id": edge["id"], "relationship_type": "connected_to"},
    )
    assert rel.status_code == 201

    graph = client.get("/api/v1/topology", headers=admin_headers).json()["data"]
    reference_ids = {n["reference_id"] for n in graph["nodes"]}
    assert core["id"] in reference_ids
    assert edge["id"] in reference_ids
    assert len(graph["links"]) >= 1


def test_topology_manual_node_and_link(client, admin_headers):
    node_a = client.post(
        "/api/v1/topology/nodes", headers=admin_headers, json={"node_type": "zone", "label": "DMZ"}
    ).json()["data"]
    node_b = client.post(
        "/api/v1/topology/nodes", headers=admin_headers, json={"node_type": "zone", "label": "Server Zone"}
    ).json()["data"]

    link = client.post(
        "/api/v1/topology/links",
        headers=admin_headers,
        json={"source_node_id": node_a["id"], "destination_node_id": node_b["id"], "link_type": "trunk"},
    )
    assert link.status_code == 201

    graph = client.get("/api/v1/topology", headers=admin_headers, params={"sync": False}).json()["data"]
    node_ids = {n["id"] for n in graph["nodes"]}
    assert node_a["id"] in node_ids and node_b["id"] in node_ids


def test_topology_link_rejects_unknown_node(client, admin_headers):
    response = client.post(
        "/api/v1/topology/links",
        headers=admin_headers,
        json={
            "source_node_id": "00000000-0000-0000-0000-000000000000",
            "destination_node_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TOPOLOGY_NODE_NOT_FOUND"


def test_topology_validate_flags_orphan_asset(client, admin_headers, asset_type):
    _create_asset(client, admin_headers, asset_type, "topo-orphan")
    client.get("/api/v1/topology", headers=admin_headers)  # trigger sync

    findings = client.post("/api/v1/topology/validate", headers=admin_headers).json()["data"]
    codes = {f["code"] for f in findings}
    assert "ORPHAN_ASSET" in codes


def test_topology_layout_update(client, admin_headers):
    node = client.post(
        "/api/v1/topology/nodes", headers=admin_headers, json={"node_type": "site", "label": "HQ"}
    ).json()["data"]

    response = client.put(
        "/api/v1/topology/layout", headers=admin_headers, json={"positions": [{"node_id": node["id"], "x": 100, "y": 200}]}
    )
    assert response.status_code == 200
    assert response.json()["data"]["updated"] == 1


def test_viewer_cannot_edit_topology(client, viewer_headers):
    response = client.post(
        "/api/v1/topology/nodes", headers=viewer_headers, json={"node_type": "site", "label": "denied"}
    )
    assert response.status_code == 403
