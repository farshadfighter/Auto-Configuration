def _create_asset(client, headers, asset_type, name, **extra):
    payload = {"name": name, "asset_type_id": str(asset_type.id), **extra}
    return client.post("/api/v1/assets", headers=headers, json=payload).json()["data"]


def _job_ready_for_approval(client, headers, asset_type, name):
    asset = _create_asset(client, headers, asset_type, name.replace(" ", "-"))
    job = client.post(
        "/api/v1/configuration/jobs", headers=headers, json={"name": name, "justification_ref": "TICKET-1"}
    ).json()["data"]
    client.post(
        f"/api/v1/configuration/jobs/{job['id']}/objects",
        headers=headers,
        json={"asset_id": asset["id"], "technology": "cisco_iosxe", "object_type": "vlan", "parameters": {"vlan_id": 31, "name": "Data"}},
    )
    client.post(f"/api/v1/configuration/jobs/{job['id']}/generate", headers=headers)
    client.post(f"/api/v1/configuration/jobs/{job['id']}/validate", headers=headers)
    submit = client.post(f"/api/v1/configuration/jobs/{job['id']}/submit-approval", headers=headers)
    assert submit.status_code == 200, submit.text
    return job


def test_no_notifications_initially(client, approver_headers):
    response = client.get("/api/v1/notifications", headers=approver_headers)
    assert response.status_code == 200
    assert response.json()["data"] == []
    count = client.get("/api/v1/notifications/unread-count", headers=approver_headers).json()["data"]
    assert count["count"] == 0


def test_submitting_job_for_approval_notifies_approvers(client, admin_headers, approver_headers, asset_type):
    _job_ready_for_approval(client, admin_headers, asset_type, "notify-approvers")

    notifications = client.get("/api/v1/notifications", headers=approver_headers).json()["data"]
    assert any(n["type"] == "approval_requested" for n in notifications)

    count = client.get("/api/v1/notifications/unread-count", headers=approver_headers).json()["data"]
    assert count["count"] >= 1


def test_notification_not_sent_to_users_without_approve_permission(client, admin_headers, viewer_headers, asset_type):
    _job_ready_for_approval(client, admin_headers, asset_type, "no-notify-viewer")

    notifications = client.get("/api/v1/notifications", headers=viewer_headers).json()["data"]
    assert notifications == []


def test_mark_notification_read(client, admin_headers, approver_headers, asset_type):
    _job_ready_for_approval(client, admin_headers, asset_type, "mark-read")
    notification = client.get("/api/v1/notifications", headers=approver_headers).json()["data"][0]
    assert notification["is_read"] is False

    response = client.post(f"/api/v1/notifications/{notification['id']}/read", headers=approver_headers)
    assert response.status_code == 200
    assert response.json()["data"]["is_read"] is True

    count = client.get("/api/v1/notifications/unread-count", headers=approver_headers).json()["data"]
    assert count["count"] == 0


def test_mark_all_read(client, admin_headers, approver_headers, asset_type):
    _job_ready_for_approval(client, admin_headers, asset_type, "mark-all-1")
    _job_ready_for_approval(client, admin_headers, asset_type, "mark-all-2")

    response = client.post("/api/v1/notifications/read-all", headers=approver_headers)
    assert response.status_code == 200
    assert response.json()["data"]["marked_read"] >= 2

    count = client.get("/api/v1/notifications/unread-count", headers=approver_headers).json()["data"]
    assert count["count"] == 0


def test_cannot_mark_someone_elses_notification_read(client, admin_headers, approver_headers, viewer_headers, asset_type):
    _job_ready_for_approval(client, admin_headers, asset_type, "cross-user")
    notification = client.get("/api/v1/notifications", headers=approver_headers).json()["data"][0]

    response = client.post(f"/api/v1/notifications/{notification['id']}/read", headers=viewer_headers)
    assert response.status_code == 404
