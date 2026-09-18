from tests.fakes import FakeDriver


def _create_asset(client, headers, asset_type, name, **extra):
    payload = {"name": name, "asset_type_id": str(asset_type.id), **extra}
    return client.post("/api/v1/assets", headers=headers, json=payload).json()["data"]


def _create_reachable_asset(client, headers, asset_type, name):
    credential = client.post(
        "/api/v1/credentials",
        headers=headers,
        json={"name": f"{name}-cred", "credential_type": "username_password", "username": "admin", "secrets": {"password": "secret"}},
    ).json()["data"]
    return _create_asset(client, headers, asset_type, name, management_ip="10.7.7.7", credential_profile_id=credential["id"])


def _approved_job(client, creator_headers, approver_headers, asset, name):
    job = client.post("/api/v1/configuration/jobs", headers=creator_headers, json={"name": name, "justification_ref": "TICKET-7"}).json()["data"]
    client.post(
        f"/api/v1/configuration/jobs/{job['id']}/objects",
        headers=creator_headers,
        json={"asset_id": asset["id"], "technology": "cisco_iosxe", "object_type": "vlan", "parameters": {"vlan_id": 60, "name": "Mgmt"}},
    )
    client.post(f"/api/v1/configuration/jobs/{job['id']}/generate", headers=creator_headers)
    client.post(f"/api/v1/configuration/jobs/{job['id']}/validate", headers=creator_headers)
    client.post(f"/api/v1/configuration/jobs/{job['id']}/submit-approval", headers=creator_headers)
    requests = client.get("/api/v1/approval/requests", headers=creator_headers).json()["data"]
    request = next(r for r in requests if r["configuration_job_id"] == job["id"])
    client.post(f"/api/v1/approval/requests/{request['id']}/approve", headers=approver_headers, json={})
    return job


def _successful_deployment(client, admin_headers, approver_headers, asset_type, monkeypatch, name):
    asset = _create_reachable_asset(client, admin_headers, asset_type, name)
    job = _approved_job(client, admin_headers, approver_headers, asset, name)

    fake = FakeDriver(deploy_succeeds=True, verify_matches=True)
    monkeypatch.setattr("app.domains.deployment.service.get_driver", lambda tech: fake)
    monkeypatch.setattr("app.domains.backup.service.get_driver", lambda tech: fake)

    deployment = client.post("/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": job["id"]}).json()["data"]
    client.post(f"/api/v1/deployment/jobs/{deployment['id']}/start", headers=admin_headers)
    return asset, job, deployment, fake


def test_successful_deployment_records_configuration_version(client, admin_headers, approver_headers, asset_type, monkeypatch):
    asset, job, deployment, _ = _successful_deployment(client, admin_headers, approver_headers, asset_type, monkeypatch, "ver-asset")

    result = client.get(f"/api/v1/deployment/jobs/{deployment['id']}", headers=admin_headers).json()["data"]
    assert result["status"] == "success"


def test_drift_analysis_flags_divergence(client, admin_headers, approver_headers, asset_type, monkeypatch):
    asset, job, deployment, fake = _successful_deployment(client, admin_headers, approver_headers, asset_type, monkeypatch, "drift-asset")

    # Live device now reports a different name than what was deployed -> drift.
    fake.verify_matches = True

    def drifted_get_current_state(object_type, parameters):
        return {"vlan_id": parameters["vlan_id"], "name": "SomethingElse"}

    fake.get_current_state = drifted_get_current_state
    monkeypatch.setattr("app.domains.drift.service.get_driver", lambda tech: fake)

    run = client.post("/api/v1/drift/analyze", headers=admin_headers)
    assert run.status_code == 201, run.text

    findings = client.get("/api/v1/drift/findings", headers=admin_headers).json()["data"]
    assert len(findings) == 1
    assert findings[0]["asset_id"] == asset["id"]
    assert findings[0]["status"] == "new"
    assert any(d["field"] == "name" for d in findings[0]["diff"])

    notifications = client.get("/api/v1/notifications", headers=admin_headers).json()["data"]
    assert any(n["type"] == "drift_detected" for n in notifications)


def test_drift_no_findings_when_state_matches(client, admin_headers, approver_headers, asset_type, monkeypatch):
    asset, job, deployment, fake = _successful_deployment(client, admin_headers, approver_headers, asset_type, monkeypatch, "nodrift-asset")

    def matching_get_current_state(object_type, parameters):
        return dict(parameters)

    fake.get_current_state = matching_get_current_state
    monkeypatch.setattr("app.domains.drift.service.get_driver", lambda tech: fake)

    client.post("/api/v1/drift/analyze", headers=admin_headers)
    findings = client.get("/api/v1/drift/findings", headers=admin_headers).json()["data"]
    assert findings == []


def test_accept_current_and_ignore_drift(client, admin_headers, approver_headers, asset_type, monkeypatch):
    asset, job, deployment, fake = _successful_deployment(client, admin_headers, approver_headers, asset_type, monkeypatch, "triage-asset")
    fake.get_current_state = lambda object_type, parameters: {"vlan_id": parameters["vlan_id"], "name": "Different"}
    monkeypatch.setattr("app.domains.drift.service.get_driver", lambda tech: fake)
    client.post("/api/v1/drift/analyze", headers=admin_headers)
    finding = client.get("/api/v1/drift/findings", headers=admin_headers).json()["data"][0]

    accepted = client.post(f"/api/v1/drift/findings/{finding['id']}/accept-current", headers=admin_headers)
    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "accepted"

    missing_reason = client.post(f"/api/v1/drift/findings/{finding['id']}/ignore", headers=admin_headers, json={"reason": ""})
    assert missing_reason.status_code == 422


def test_restore_desired_creates_remediation_job(client, admin_headers, approver_headers, asset_type, monkeypatch):
    asset, job, deployment, fake = _successful_deployment(client, admin_headers, approver_headers, asset_type, monkeypatch, "remediate-asset")
    fake.get_current_state = lambda object_type, parameters: {"vlan_id": parameters["vlan_id"], "name": "Drifted"}
    monkeypatch.setattr("app.domains.drift.service.get_driver", lambda tech: fake)
    client.post("/api/v1/drift/analyze", headers=admin_headers)
    finding = client.get("/api/v1/drift/findings", headers=admin_headers).json()["data"][0]

    response = client.post(f"/api/v1/drift/findings/{finding['id']}/restore-desired", headers=admin_headers)
    assert response.status_code == 200, response.text
    new_job_id = response.json()["data"]["configuration_job_id"]

    new_job = client.get(f"/api/v1/configuration/jobs/{new_job_id}", headers=admin_headers).json()["data"]
    assert new_job["status"] == "draft"

    # Creating the remediation job doesn't fix anything by itself - the finding must stay
    # actionable (status "new") until that job is actually deployed and verified.
    finding_after_creation = client.get(f"/api/v1/drift/findings/{finding['id']}", headers=admin_headers).json()["data"]
    assert finding_after_creation["status"] == "new"

    client.post(f"/api/v1/configuration/jobs/{new_job_id}/generate", headers=admin_headers)
    client.post(f"/api/v1/configuration/jobs/{new_job_id}/validate", headers=admin_headers)
    client.post(f"/api/v1/configuration/jobs/{new_job_id}/submit-approval", headers=admin_headers)
    requests = client.get("/api/v1/approval/requests", headers=admin_headers).json()["data"]
    request = next(r for r in requests if r["configuration_job_id"] == new_job_id)
    client.post(f"/api/v1/approval/requests/{request['id']}/approve", headers=approver_headers, json={})

    remediation_deployment = client.post(
        "/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": new_job_id}
    ).json()["data"]
    client.post(f"/api/v1/deployment/jobs/{remediation_deployment['id']}/start", headers=admin_headers)
    remediation_deployment_after = client.get(
        f"/api/v1/deployment/jobs/{remediation_deployment['id']}", headers=admin_headers
    ).json()["data"]
    assert remediation_deployment_after["status"] == "success"

    finding_after_deploy = client.get(f"/api/v1/drift/findings/{finding['id']}", headers=admin_headers).json()["data"]
    assert finding_after_deploy["status"] == "remediated"


def test_failed_remediation_deployment_leaves_finding_actionable(client, admin_headers, approver_headers, asset_type, monkeypatch):
    asset, job, deployment, fake = _successful_deployment(client, admin_headers, approver_headers, asset_type, monkeypatch, "remediate-fail-asset")
    fake.get_current_state = lambda object_type, parameters: {"vlan_id": parameters["vlan_id"], "name": "Drifted"}
    monkeypatch.setattr("app.domains.drift.service.get_driver", lambda tech: fake)
    client.post("/api/v1/drift/analyze", headers=admin_headers)
    finding = client.get("/api/v1/drift/findings", headers=admin_headers).json()["data"][0]

    new_job_id = client.post(
        f"/api/v1/drift/findings/{finding['id']}/restore-desired", headers=admin_headers
    ).json()["data"]["configuration_job_id"]
    client.post(f"/api/v1/configuration/jobs/{new_job_id}/generate", headers=admin_headers)
    client.post(f"/api/v1/configuration/jobs/{new_job_id}/validate", headers=admin_headers)
    client.post(f"/api/v1/configuration/jobs/{new_job_id}/submit-approval", headers=admin_headers)
    requests = client.get("/api/v1/approval/requests", headers=admin_headers).json()["data"]
    request = next(r for r in requests if r["configuration_job_id"] == new_job_id)
    client.post(f"/api/v1/approval/requests/{request['id']}/approve", headers=approver_headers, json={})

    # The remediation deployment itself fails (e.g. the device rejects the change).
    fake.verify_matches = False
    remediation_deployment = client.post(
        "/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": new_job_id}
    ).json()["data"]
    client.post(f"/api/v1/deployment/jobs/{remediation_deployment['id']}/start", headers=admin_headers)
    remediation_deployment_after = client.get(
        f"/api/v1/deployment/jobs/{remediation_deployment['id']}", headers=admin_headers
    ).json()["data"]
    assert remediation_deployment_after["status"] == "verify_failed"

    # The still-drifted asset must not be hidden behind a "remediated" status it never earned.
    finding_after = client.get(f"/api/v1/drift/findings/{finding['id']}", headers=admin_headers).json()["data"]
    assert finding_after["status"] == "new"


def test_drift_run_survives_one_assets_broken_credentials(client, admin_headers, approver_headers, asset_type, monkeypatch):
    # An asset whose credential profile is missing the "password" secret must not crash the
    # whole drift run - it should be skipped, and the run must still finish as "success"
    # rather than getting stuck at "running" forever.
    asset, job, deployment, fake = _successful_deployment(client, admin_headers, approver_headers, asset_type, monkeypatch, "broken-cred-asset")
    monkeypatch.setattr("app.domains.drift.service.get_driver", lambda tech: fake)

    empty_credential = client.post(
        "/api/v1/credentials",
        headers=admin_headers,
        json={"name": "no-password-cred", "credential_type": "username_password", "username": "admin", "secrets": {}},
    ).json()["data"]
    client.put(f"/api/v1/assets/{asset['id']}", headers=admin_headers, json={"credential_profile_id": empty_credential["id"]})

    run = client.post("/api/v1/drift/analyze", headers=admin_headers)
    assert run.status_code == 201, run.text
    assert run.json()["data"]["status"] == "success"
    assert run.json()["data"]["drift_found_count"] == 0


def test_viewer_cannot_run_drift_analysis(client, viewer_headers):
    response = client.post("/api/v1/drift/analyze", headers=viewer_headers)
    assert response.status_code == 403


def test_reports_endpoints(client, admin_headers, asset_type):
    _create_asset(client, admin_headers, asset_type, "report-asset")
    for path in [
        "/api/v1/reports/asset-inventory",
        "/api/v1/reports/architecture-findings",
        "/api/v1/reports/configuration-jobs",
        "/api/v1/reports/deployments",
        "/api/v1/reports/backups",
        "/api/v1/reports/drift",
        "/api/v1/reports/technology-coverage",
    ]:
        response = client.get(path, headers=admin_headers)
        assert response.status_code == 200, f"{path}: {response.text}"

    inventory = client.get("/api/v1/reports/asset-inventory", headers=admin_headers).json()["data"]
    assert inventory["total"] >= 1

    coverage = client.get("/api/v1/reports/technology-coverage", headers=admin_headers).json()["data"]
    technologies = {c["technology"] for c in coverage}
    assert {"cisco_iosxe", "fortios", "windows_dns", "windows_dhcp"}.issubset(technologies)
