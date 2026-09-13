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
    # Perimeter Firewall carries a redundancy_min: 2 scale rule, so a single firewall isn't
    # enough to fully satisfy it - two are needed to avoid a capacity gap.
    _create_asset(
        client,
        admin_headers,
        asset_type,
        "edge-fw-01",
        safe_pin="internet_edge",
        asset_type_id=str(firewall_type.id),
    )
    _create_asset(
        client,
        admin_headers,
        asset_type,
        "edge-fw-02",
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
    # Two firewall assets already exist in this PIN, satisfying the redundancy floor, so
    # "Perimeter Firewall (NGFW)" must NOT also show up as a recommended/missing component.
    assert "Perimeter Firewall (NGFW)" not in recommended_names


def test_viewer_cannot_generate_safe_recommendation(client, viewer_headers):
    response = client.post(
        "/api/v1/architecture-recommendations/safe", headers=viewer_headers, json={"name": "Denied"}
    )
    assert response.status_code == 403


def _link(client, headers, source_id, target_id):
    response = client.post(
        "/api/v1/assets/relationships",
        headers=headers,
        json={"source_asset_id": source_id, "target_asset_id": target_id, "relationship_type": "connected_to"},
    )
    assert response.status_code == 201, response.text


def _get_path_analysis(client, headers):
    response = client.get("/api/v1/architecture-recommendations/safe/path-analysis", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_path_analysis_flags_unprotected_direct_link(client, admin_headers, asset_type):
    edge_router = _create_asset(client, admin_headers, asset_type, "path-edge-rtr", safe_pin="internet_edge")
    core_switch = _create_asset(client, admin_headers, asset_type, "path-core-sw", safe_pin="campus_core")
    _link(client, admin_headers, edge_router["id"], core_switch["id"])

    findings = _get_path_analysis(client, admin_headers)
    boundary_findings = [
        f for f in findings if {f["pin_a"], f["pin_b"]} == {"internet_edge", "campus_core"} and f["source_asset_id"] == edge_router["id"]
    ]
    assert len(boundary_findings) == 1
    finding = boundary_findings[0]
    assert finding["protected"] is False
    assert finding["required_capability"] == "firewall"
    assert finding["path_asset_names"] == ["path-edge-rtr", "path-core-sw"]


def test_path_analysis_marks_protected_when_firewall_sits_on_the_real_path(client, admin_headers, asset_type, db_session):
    from app.domains.assets.models import AssetType

    firewall_type = AssetType(code="firewall", name="Firewall")
    db_session.add(firewall_type)
    db_session.commit()

    edge_router = _create_asset(client, admin_headers, asset_type, "path-edge-rtr-2", safe_pin="internet_edge")
    firewall = _create_asset(client, admin_headers, asset_type, "path-fw", asset_type_id=str(firewall_type.id))
    core_switch = _create_asset(client, admin_headers, asset_type, "path-core-sw-2", safe_pin="campus_core")
    _link(client, admin_headers, edge_router["id"], firewall["id"])
    _link(client, admin_headers, firewall["id"], core_switch["id"])

    findings = _get_path_analysis(client, admin_headers)
    boundary_findings = [f for f in findings if f["source_asset_id"] == edge_router["id"] and f["target_asset_id"] == core_switch["id"]]
    assert len(boundary_findings) == 1
    finding = boundary_findings[0]
    assert finding["protected"] is True
    assert "path-fw" in finding["path_asset_names"]


def test_generate_recommendation_overrides_pin_ownership_when_real_path_is_unprotected(client, admin_headers, asset_type, db_session):
    """An org can own a firewall and still have an unprotected real path if that firewall
    isn't actually positioned between the two zones - the generated diagram must reflect the
    real path, not just "do we own a firewall somewhere in this PIN"."""
    from app.domains.assets.models import AssetType

    firewall_type = AssetType(code="firewall", name="Firewall")
    db_session.add(firewall_type)
    db_session.commit()

    edge_router = _create_asset(client, admin_headers, asset_type, "path-edge-rtr-3", safe_pin="internet_edge")
    core_switch = _create_asset(client, admin_headers, asset_type, "path-core-sw-3", safe_pin="campus_core")
    # The firewall exists and is classified into internet_edge, but it's NOT wired into the
    # real path between the router and the core switch - it's off connected to nothing
    # relevant here, e.g. a management-only box.
    _create_asset(
        client, admin_headers, asset_type, "path-fw-unused", safe_pin="internet_edge", asset_type_id=str(firewall_type.id)
    )
    _link(client, admin_headers, edge_router["id"], core_switch["id"])

    response = client.post(
        "/api/v1/architecture-recommendations/safe", headers=admin_headers, json={"name": "SAFE Path Override Test"}
    )
    version_id = response.json()["data"]["version_id"]
    graph = client.get(f"/api/v1/designs/versions/{version_id}", headers=admin_headers).json()["data"]

    edge_components = [c for c in graph["components"] if c["properties"]["safe_pin"] == "internet_edge"]
    recommended = {c["name"]: c["properties"] for c in edge_components if c["properties"]["recommended"]}
    assert "Perimeter Firewall (NGFW)" in recommended
    assert recommended["Perimeter Firewall (NGFW)"]["reason"] == "unprotected_path"


def test_viewer_can_view_path_analysis(client, viewer_headers):
    response = client.get("/api/v1/architecture-recommendations/safe/path-analysis", headers=viewer_headers)
    assert response.status_code == 200


def test_scale_gaps_endpoint_flags_redundancy_shortfall(client, admin_headers, asset_type, db_session):
    """Perimeter Firewall carries a redundancy_min: 2 scale rule - a single firewall in
    Internet Edge is a real capacity gap, not just a present/absent check."""
    from app.domains.assets.models import AssetType

    firewall_type = AssetType(code="firewall", name="Firewall")
    db_session.add(firewall_type)
    db_session.commit()

    _create_asset(client, admin_headers, asset_type, "edge-rtr-scale", safe_pin="internet_edge")
    _create_asset(
        client, admin_headers, asset_type, "edge-fw-scale", safe_pin="internet_edge", asset_type_id=str(firewall_type.id)
    )

    response = client.get("/api/v1/architecture-recommendations/safe/scale-gaps", headers=admin_headers)
    assert response.status_code == 200, response.text
    scale_gaps = response.json()["data"]["scale_gaps"]
    firewall_gap = next(g for g in scale_gaps if g["pin"] == "internet_edge" and g["component_type"] == "firewall")
    assert firewall_gap["existing_count"] == 1
    assert firewall_gap["required_count"] == 2


def test_scale_gap_recommends_second_core_switch_once_access_layer_grows(client, admin_headers, asset_type, db_session):
    """Core Switch scales off the Campus Access layer's size (metric_pin: campus_access, per:
    30, redundancy_min: 2) - past 30 access-layer assets, more than the baseline redundant pair
    is called for."""
    from app.domains.assets.models import Asset, SafePin

    # 61 classified Campus Access assets -> ceil(61 / 30) = 3 required Core Switches.
    for i in range(61):
        db_session.add(
            Asset(asset_code=f"AST-ACC-{i}", name=f"access-sw-{i}", asset_type_id=asset_type.id, safe_pin=SafePin.CAMPUS_ACCESS)
        )
    # Only one real Core Switch exists so far (matched via the "core" keyword in its name).
    db_session.add(Asset(asset_code="AST-CORE-1", name="core-sw-1", asset_type_id=asset_type.id, safe_pin=SafePin.CAMPUS_CORE))
    db_session.commit()

    response = client.get("/api/v1/architecture-recommendations/safe/scale-gaps", headers=admin_headers)
    assert response.status_code == 200, response.text
    scale_gaps = response.json()["data"]["scale_gaps"]
    core_gap = next(g for g in scale_gaps if g["pin"] == "campus_core" and g["component_type"] == "switch")
    assert core_gap["metric_asset_count"] == 61
    assert core_gap["existing_count"] == 1
    assert core_gap["required_count"] == 3


def test_location_gap_flags_branch_site_missing_components(client, admin_headers, asset_type, db_session):
    """Branch is a per_location PIN: every site with branch-classified assets should have its
    own router/firewall/switch, and a gap at one site isn't hidden by another site having it."""
    from app.domains.assets.models import Asset, AssetType, Location, SafePin

    firewall_type = AssetType(code="firewall", name="Firewall")
    switch_type = AssetType(code="switch", name="Switch")
    db_session.add_all([firewall_type, switch_type])
    fully_covered = Location(name="Fully Covered Branch")
    partially_covered = Location(name="Partially Covered Branch")
    db_session.add_all([fully_covered, partially_covered])
    db_session.commit()

    # Fully covered site: router + firewall + switch.
    db_session.add(
        Asset(
            asset_code="AST-BR1-RTR",
            name="branch1-rtr",
            asset_type_id=asset_type.id,
            safe_pin=SafePin.BRANCH,
            location_id=fully_covered.id,
        )
    )
    db_session.add(
        Asset(
            asset_code="AST-BR1-FW",
            name="branch1-fw",
            asset_type_id=firewall_type.id,
            safe_pin=SafePin.BRANCH,
            location_id=fully_covered.id,
        )
    )
    db_session.add(
        Asset(
            asset_code="AST-BR1-SW",
            name="branch1-sw",
            asset_type_id=switch_type.id,
            safe_pin=SafePin.BRANCH,
            location_id=fully_covered.id,
        )
    )
    # Partially covered site: router only - missing firewall and switch.
    db_session.add(
        Asset(
            asset_code="AST-BR2-RTR",
            name="branch2-rtr",
            asset_type_id=asset_type.id,
            safe_pin=SafePin.BRANCH,
            location_id=partially_covered.id,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/architecture-recommendations/safe/scale-gaps", headers=admin_headers)
    assert response.status_code == 200, response.text
    location_gaps = response.json()["data"]["location_gaps"]

    fully_covered_gaps = [g for g in location_gaps if g["location_id"] == str(fully_covered.id)]
    assert fully_covered_gaps == []

    partially_covered_gaps = {g["missing_component_type"] for g in location_gaps if g["location_id"] == str(partially_covered.id)}
    assert partially_covered_gaps == {"firewall", "switch"}


def test_generate_safe_recommendation_response_includes_gap_reports(client, admin_headers, asset_type):
    response = client.post(
        "/api/v1/architecture-recommendations/safe", headers=admin_headers, json={"name": "SAFE Gap Report Test"}
    )
    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert "scale_gaps" in body
    assert "location_gaps" in body


def test_viewer_can_view_scale_gaps(client, viewer_headers):
    response = client.get("/api/v1/architecture-recommendations/safe/scale-gaps", headers=viewer_headers)
    assert response.status_code == 200
