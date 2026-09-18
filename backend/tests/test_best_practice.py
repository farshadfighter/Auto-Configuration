def _create_asset(client, headers, asset_type, name, **extra):
    payload = {"name": name, "asset_type_id": str(asset_type.id), **extra}
    response = client.post("/api/v1/assets", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_analyze_flags_managed_asset_missing_ip(client, admin_headers, asset_type):
    _create_asset(client, admin_headers, asset_type, "no-ip-switch", managed="managed")

    run = client.post("/api/v1/best-practice/analyze", headers=admin_headers)
    assert run.status_code == 201, run.text
    assert run.json()["data"]["findings_created"] >= 1

    findings = client.get("/api/v1/best-practice/findings", headers=admin_headers).json()["data"]
    codes = {f["rule_code"] for f in findings}
    assert "BP-ASSET-002" in codes


def test_analyze_does_not_flag_compliant_asset(client, admin_headers, asset_type):
    _create_asset(
        client,
        admin_headers,
        asset_type,
        "compliant-switch",
        managed="managed",
        management_ip="10.5.5.5",
    )
    run = client.post("/api/v1/best-practice/analyze", headers=admin_headers)
    findings = client.get("/api/v1/best-practice/findings", headers=admin_headers).json()["data"]
    matching = [f for f in findings if f["rule_code"] == "BP-ASSET-002"]
    assert matching == []
    assert run.status_code == 201


def test_finding_affected_assets_are_linked(client, admin_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "linked-switch", managed="managed")
    client.post("/api/v1/best-practice/analyze", headers=admin_headers)

    findings = client.get("/api/v1/best-practice/findings", headers=admin_headers).json()["data"]
    target = next(f for f in findings if f["rule_code"] == "BP-ASSET-002")
    assert asset["id"] in target["affected_asset_ids"]


def test_accept_finding(client, admin_headers, asset_type):
    _create_asset(client, admin_headers, asset_type, "accept-me", managed="managed")
    client.post("/api/v1/best-practice/analyze", headers=admin_headers)
    findings = client.get("/api/v1/best-practice/findings", headers=admin_headers).json()["data"]
    finding_id = next(f["id"] for f in findings if f["rule_code"] == "BP-ASSET-002")

    response = client.post(f"/api/v1/best-practice/findings/{finding_id}/accept", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "accepted"


def test_ignore_finding_requires_reason(client, admin_headers, asset_type):
    _create_asset(client, admin_headers, asset_type, "ignore-me", managed="managed")
    client.post("/api/v1/best-practice/analyze", headers=admin_headers)
    findings = client.get("/api/v1/best-practice/findings", headers=admin_headers).json()["data"]
    finding_id = next(f["id"] for f in findings if f["rule_code"] == "BP-ASSET-002")

    missing_reason = client.post(f"/api/v1/best-practice/findings/{finding_id}/ignore", headers=admin_headers, json={"reason": ""})
    assert missing_reason.status_code == 422

    with_reason = client.post(
        f"/api/v1/best-practice/findings/{finding_id}/ignore",
        headers=admin_headers,
        json={"reason": "Air-gapped lab device, IP intentionally unset"},
    )
    assert with_reason.status_code == 200
    assert with_reason.json()["data"]["status"] == "ignored"
    assert with_reason.json()["data"]["ignore_reason"]


def test_rerun_does_not_duplicate_untouched_findings(client, admin_headers, asset_type):
    _create_asset(client, admin_headers, asset_type, "rerun-switch", managed="managed")
    client.post("/api/v1/best-practice/analyze", headers=admin_headers)
    first_count = len(client.get("/api/v1/best-practice/findings", headers=admin_headers).json()["data"])

    client.post("/api/v1/best-practice/analyze", headers=admin_headers)
    second_count = len(client.get("/api/v1/best-practice/findings", headers=admin_headers).json()["data"])
    assert first_count == second_count


def test_rerun_preserves_triaged_findings(client, admin_headers, asset_type):
    _create_asset(client, admin_headers, asset_type, "triaged-switch", managed="managed")
    client.post("/api/v1/best-practice/analyze", headers=admin_headers)
    findings = client.get("/api/v1/best-practice/findings", headers=admin_headers).json()["data"]
    finding_id = next(f["id"] for f in findings if f["rule_code"] == "BP-ASSET-002")
    client.post(f"/api/v1/best-practice/findings/{finding_id}/accept", headers=admin_headers)

    client.post("/api/v1/best-practice/analyze", headers=admin_headers)
    refreshed = client.get(f"/api/v1/best-practice/findings/{finding_id}", headers=admin_headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["data"]["status"] == "accepted"


def test_router_without_oob_management_flagged_bp_net_003(client, admin_headers, asset_type):
    _create_asset(client, admin_headers, asset_type, "no-oob-router")
    client.post("/api/v1/best-practice/analyze", headers=admin_headers)
    findings = client.get("/api/v1/best-practice/findings", headers=admin_headers).json()["data"]
    assert any(f["rule_code"] == "BP-NET-003" for f in findings)


def test_router_with_oob_management_not_flagged_bp_net_003(client, admin_headers, asset_type):
    _create_asset(client, admin_headers, asset_type, "oob-router", asset_metadata={"oob_management": True})
    client.post("/api/v1/best-practice/analyze", headers=admin_headers)
    findings = client.get("/api/v1/best-practice/findings", headers=admin_headers).json()["data"]
    assert not any(f["rule_code"] == "BP-NET-003" for f in findings)


def test_viewer_cannot_run_analysis(client, viewer_headers):
    response = client.post("/api/v1/best-practice/analyze", headers=viewer_headers)
    assert response.status_code == 403
