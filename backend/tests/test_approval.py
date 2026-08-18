def _create_asset(client, headers, asset_type, name, **extra):
    payload = {"name": name, "asset_type_id": str(asset_type.id), **extra}
    return client.post("/api/v1/assets", headers=headers, json=payload).json()["data"]


def _job_ready_for_approval(client, headers, asset_type, name="Approval flow job"):
    asset = _create_asset(client, headers, asset_type, name.replace(" ", "-"))
    job = client.post(
        "/api/v1/configuration/jobs", headers=headers, json={"name": name, "justification_ref": "TICKET-1"}
    ).json()["data"]
    client.post(
        f"/api/v1/configuration/jobs/{job['id']}/objects",
        headers=headers,
        json={"asset_id": asset["id"], "technology": "cisco_iosxe", "object_type": "vlan", "parameters": {"vlan_id": 30, "name": "Data"}},
    )
    client.post(f"/api/v1/configuration/jobs/{job['id']}/generate", headers=headers)
    client.post(f"/api/v1/configuration/jobs/{job['id']}/validate", headers=headers)
    submit = client.post(f"/api/v1/configuration/jobs/{job['id']}/submit-approval", headers=headers)
    assert submit.status_code == 200, submit.text
    return job


def _find_request_for_job(client, headers, job_id):
    requests = client.get("/api/v1/approval/requests", headers=headers).json()["data"]
    return next(r for r in requests if r["configuration_job_id"] == job_id)


def test_submitting_job_creates_pending_approval_request(client, admin_headers, asset_type):
    job = _job_ready_for_approval(client, admin_headers, asset_type, "req-created")
    request = _find_request_for_job(client, admin_headers, job["id"])
    assert request["status"] == "pending"
    assert request["required_approvals"] == 1  # low risk, no deletes


def test_approve_moves_job_to_approved(client, admin_headers, approver_headers, asset_type):
    # admin creates the job; a separate Approver user approves it (segregation of duties).
    job = _job_ready_for_approval(client, admin_headers, asset_type, "req-approve")
    request = _find_request_for_job(client, admin_headers, job["id"])

    response = client.post(f"/api/v1/approval/requests/{request['id']}/approve", headers=approver_headers, json={"comment": "LGTM"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "approved"

    job_after = client.get(f"/api/v1/configuration/jobs/{job['id']}", headers=admin_headers).json()["data"]
    assert job_after["status"] == "approved"


def test_reject_requires_comment(client, admin_headers, approver_headers, asset_type):
    job = _job_ready_for_approval(client, admin_headers, asset_type, "req-reject")
    request = _find_request_for_job(client, admin_headers, job["id"])

    missing = client.post(f"/api/v1/approval/requests/{request['id']}/reject", headers=approver_headers, json={"comment": ""})
    assert missing.status_code == 422

    ok = client.post(f"/api/v1/approval/requests/{request['id']}/reject", headers=approver_headers, json={"comment": "Not compliant"})
    assert ok.status_code == 200
    assert ok.json()["data"]["status"] == "rejected"

    job_after = client.get(f"/api/v1/configuration/jobs/{job['id']}", headers=admin_headers).json()["data"]
    assert job_after["status"] == "rejected"


def test_cannot_approve_already_resolved_request(client, admin_headers, approver_headers, asset_type):
    job = _job_ready_for_approval(client, admin_headers, asset_type, "req-dup")
    request = _find_request_for_job(client, admin_headers, job["id"])
    client.post(f"/api/v1/approval/requests/{request['id']}/approve", headers=approver_headers, json={})

    second = client.post(f"/api/v1/approval/requests/{request['id']}/approve", headers=approver_headers, json={})
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "APPROVAL_ALREADY_RESOLVED"


def test_creator_cannot_approve_own_job(client, admin_headers, approver_headers, asset_type):
    job = _job_ready_for_approval(client, admin_headers, asset_type, "req-self")
    request = _find_request_for_job(client, admin_headers, job["id"])

    self_approve = client.post(f"/api/v1/approval/requests/{request['id']}/approve", headers=admin_headers, json={})
    assert self_approve.status_code == 409
    assert self_approve.json()["error"]["code"] == "SELF_APPROVAL_NOT_ALLOWED"

    other_approve = client.post(f"/api/v1/approval/requests/{request['id']}/approve", headers=approver_headers, json={})
    assert other_approve.status_code == 200


def test_viewer_cannot_approve(client, admin_headers, viewer_headers, asset_type):
    job = _job_ready_for_approval(client, admin_headers, asset_type, "req-viewer")
    request = _find_request_for_job(client, admin_headers, job["id"])
    response = client.post(f"/api/v1/approval/requests/{request['id']}/approve", headers=viewer_headers, json={})
    assert response.status_code == 403
