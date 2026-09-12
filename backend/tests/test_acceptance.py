"""End-to-end acceptance test mirroring spec section 96/129: the full chain from asset
discovery through to a deployed, versioned, drift-checked, audited change - as one continuous
workflow through the real API, not isolated per-domain tests. Uses FakeDriver for the live
device I/O steps (matching spec section 95's mock-device testing expectation)."""

from tests.fakes import FakeDriver


def test_full_lifecycle_asset_to_audit(client, admin_headers, approver_headers, asset_type, monkeypatch):
    # 1. Asset: create the switch NGFabric will manage.
    credential = client.post(
        "/api/v1/credentials",
        headers=admin_headers,
        json={"name": "accept-cred", "credential_type": "username_password", "username": "admin", "secrets": {"password": "secret"}},
    ).json()["data"]
    asset = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={
            "name": "accept-core-sw",
            "asset_type_id": str(asset_type.id),
            "management_ip": "10.99.0.1",
            "credential_profile_id": credential["id"],
            "criticality": "high",
            "managed": "managed",
        },
    ).json()["data"]
    assert asset["asset_code"].startswith("AST-")

    # 2. Discovery: a CSV import reconciles a second asset (proves the discovery pipeline
    #    independently of the manually-created one above).
    csv_content = f"name,asset_type_code,management_ip\naccept-edge-sw,{asset_type.code},10.99.0.2\n"
    discovery_job = client.post(
        "/api/v1/discovery/jobs", headers=admin_headers, json={"method": "csv_import", "scope": {"csv_content": csv_content}}
    ).json()["data"]
    assert discovery_job["status"] == "success"
    assert discovery_job["discovered_count"] == 1

    # 3. Topology: sync derives nodes from both assets; link them so neither is orphaned.
    graph = client.get("/api/v1/topology", headers=admin_headers).json()["data"]
    edge_asset = client.get("/api/v1/assets?search=accept-edge-sw", headers=admin_headers).json()["data"][0]
    node_by_asset = {n["reference_id"]: n["id"] for n in graph["nodes"]}
    client.post(
        "/api/v1/topology/links",
        headers=admin_headers,
        json={"source_node_id": node_by_asset[asset["id"]], "destination_node_id": node_by_asset[edge_asset["id"]], "link_type": "uplink"},
    )

    # 4. Finding: best-practice analysis flags the discovered edge asset for having no site
    #    assigned (discovery doesn't infer sites - BP-ASSET-003 has no applies_to filter, so
    #    it also flags our manually-created asset for the same reason; that's correct, not a
    #    bug in the test, since we didn't set site_id on it either).
    run = client.post("/api/v1/best-practice/analyze", headers=admin_headers).json()["data"]
    assert run["status"] == "success"
    findings = client.get("/api/v1/best-practice/findings", headers=admin_headers).json()["data"]
    edge_findings = [f for f in findings if edge_asset["id"] in f["affected_asset_ids"] and f["rule_code"] == "BP-ASSET-003"]
    assert len(edge_findings) == 1

    # 5. Design: a minimal approved design referencing the finding, to prove the design
    #    domain's own lifecycle (independent of whether Configuration actually consumes it -
    #    Configuration in MVP scope runs standalone in Manual mode; source_type=design is
    #    schema-ready but wiring a design's components into a configuration job automatically
    #    is intentionally out of MVP scope, see the Configuration Core commit).
    design = client.post("/api/v1/designs", headers=admin_headers, json={"name": "Accept design", "mode": "manual"}).json()["data"]
    design_detail = client.get(f"/api/v1/designs/{design['id']}", headers=admin_headers).json()["data"]
    version_id = design_detail["latest_version"]["id"]
    client.post(
        f"/api/v1/designs/versions/{version_id}/components",
        headers=admin_headers,
        json={"component_type": "switch", "name": "accept-core-sw"},
    )
    client.post(
        f"/api/v1/designs/versions/{version_id}/map-recommendation",
        headers=admin_headers,
        json={"finding_id": edge_findings[0]["id"]},
    )
    approve_design = client.post(f"/api/v1/designs/{design['id']}/approve", headers=admin_headers, json={"comment": "ok"})
    assert approve_design.json()["data"]["status"] == "approved"

    # 6. Configuration: build a VLAN change against our asset.
    job = client.post(
        "/api/v1/configuration/jobs",
        headers=admin_headers,
        json={"name": "Acceptance VLAN change", "justification_ref": "ACCEPT-1"},
    ).json()["data"]
    client.post(
        f"/api/v1/configuration/jobs/{job['id']}/objects",
        headers=admin_headers,
        json={"asset_id": asset["id"], "technology": "cisco_iosxe", "object_type": "vlan", "parameters": {"vlan_id": 200, "name": "Acceptance"}},
    )
    generated = client.post(f"/api/v1/configuration/jobs/{job['id']}/generate", headers=admin_headers).json()["data"]
    assert generated["status"] == "generated"

    # 7. Validation: schema/capability validation passes for a well-formed VLAN.
    validated = client.post(f"/api/v1/configuration/jobs/{job['id']}/validate", headers=admin_headers).json()["data"]
    assert validated["status"] == "validated"
    diff = client.get(f"/api/v1/configuration/jobs/{job['id']}/diff", headers=admin_headers).json()["data"]
    assert diff[0]["change_type"] == "create"

    # 8. Approval: creator can't self-approve; a separate Approver can.
    submit = client.post(f"/api/v1/configuration/jobs/{job['id']}/submit-approval", headers=admin_headers)
    assert submit.json()["data"]["status"] == "pending_approval"
    requests = client.get("/api/v1/approval/requests", headers=admin_headers).json()["data"]
    approval_request = next(r for r in requests if r["configuration_job_id"] == job["id"])
    self_approve = client.post(f"/api/v1/approval/requests/{approval_request['id']}/approve", headers=admin_headers, json={})
    assert self_approve.status_code == 409
    approve = client.post(f"/api/v1/approval/requests/{approval_request['id']}/approve", headers=approver_headers, json={"comment": "go"})
    assert approve.json()["data"]["status"] == "approved"
    job_after_approval = client.get(f"/api/v1/configuration/jobs/{job['id']}", headers=admin_headers).json()["data"]
    assert job_after_approval["status"] == "approved"

    # 9-11. Backup, Deploy, Verify: the deployment pipeline takes a pre-deployment backup,
    #        applies the change, and verifies it - all through a FakeDriver standing in for
    #        the real device.
    fake = FakeDriver(deploy_succeeds=True, verify_matches=True)
    monkeypatch.setattr("app.domains.deployment.service.get_driver", lambda tech: fake)
    monkeypatch.setattr("app.domains.backup.service.get_driver", lambda tech: fake)

    deployment = client.post("/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": job["id"]}).json()["data"]
    client.post(f"/api/v1/deployment/jobs/{deployment['id']}/start", headers=admin_headers)
    deployment_after = client.get(f"/api/v1/deployment/jobs/{deployment['id']}", headers=admin_headers).json()["data"]
    assert deployment_after["status"] == "success"

    results = client.get(f"/api/v1/deployment/jobs/{deployment['id']}/results", headers=admin_headers).json()["data"]
    assert results[0]["success"] is True
    assert results[0]["verified"] is True

    backups = client.get(f"/api/v1/assets/{asset['id']}/backups", headers=admin_headers).json()["data"]
    assert any(b["backup_type"] == "pre_deployment" for b in backups)

    # 12. Version: the verified object is recorded as configuration history for the asset.
    versions = client.get(f"/api/v1/assets/{asset['id']}/configuration-versions", headers=admin_headers).json()["data"]
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["state"]["vlan_id"] == 200

    # 13. Drift: the live device now disagrees with the recorded version -> a finding appears,
    #     and restoring the desired state creates a follow-up remediation job.
    fake.get_current_state = lambda object_type, parameters: {"vlan_id": parameters["vlan_id"], "name": "Drifted"}
    monkeypatch.setattr("app.domains.drift.service.get_driver", lambda tech: fake)
    drift_run = client.post("/api/v1/drift/analyze", headers=admin_headers).json()["data"]
    assert drift_run["drift_found_count"] == 1
    drift_findings = client.get("/api/v1/drift/findings", headers=admin_headers).json()["data"]
    assert drift_findings[0]["asset_id"] == asset["id"]
    remediation = client.post(f"/api/v1/drift/findings/{drift_findings[0]['id']}/restore-desired", headers=admin_headers)
    remediation_job_id = remediation.json()["data"]["configuration_job_id"]
    remediation_job = client.get(f"/api/v1/configuration/jobs/{remediation_job_id}", headers=admin_headers).json()["data"]
    assert remediation_job["status"] == "draft"

    # 14. Audit: every state-changing step above left an immutable trail for this asset/job.
    asset_audit = client.get(f"/api/v1/audit/events?object_type=asset&object_id={asset['id']}", headers=admin_headers).json()["data"]
    assert any(e["action"] == "ASSET_CREATED" for e in asset_audit)

    job_audit = client.get(f"/api/v1/audit/events?object_type=configuration_job&object_id={job['id']}", headers=admin_headers).json()["data"]
    job_actions = {e["action"] for e in job_audit}
    assert {"CONFIG_JOB_CREATED", "CONFIG_JOB_GENERATED", "CONFIG_JOB_VALIDATED", "CONFIG_JOB_SUBMITTED_FOR_APPROVAL"}.issubset(job_actions)

    approval_audit = client.get(
        f"/api/v1/audit/events?object_type=approval_request&object_id={approval_request['id']}", headers=admin_headers
    ).json()["data"]
    assert any(e["action"] == "APPROVAL_GRANTED" for e in approval_audit)

    # Reports reflect the same reality without any separate data path.
    inventory = client.get("/api/v1/reports/asset-inventory", headers=admin_headers).json()["data"]
    assert inventory["total"] >= 2
    deployments_report = client.get("/api/v1/reports/deployments", headers=admin_headers).json()["data"]
    assert deployments_report["by_status"].get("success", 0) >= 1
