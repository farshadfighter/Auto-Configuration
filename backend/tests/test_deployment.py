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
    return _create_asset(client, headers, asset_type, name, management_ip="10.6.6.6", credential_profile_id=credential["id"])


def _approved_job(client, creator_headers, approver_headers, asset, name):
    job = client.post("/api/v1/configuration/jobs", headers=creator_headers, json={"name": name, "justification_ref": "TICKET-9"}).json()["data"]
    client.post(
        f"/api/v1/configuration/jobs/{job['id']}/objects",
        headers=creator_headers,
        json={"asset_id": asset["id"], "technology": "cisco_iosxe", "object_type": "vlan", "parameters": {"vlan_id": 40, "name": "Voice"}},
    )
    client.post(f"/api/v1/configuration/jobs/{job['id']}/generate", headers=creator_headers)
    client.post(f"/api/v1/configuration/jobs/{job['id']}/validate", headers=creator_headers)
    client.post(f"/api/v1/configuration/jobs/{job['id']}/submit-approval", headers=creator_headers)
    requests = client.get("/api/v1/approval/requests", headers=creator_headers).json()["data"]
    request = next(r for r in requests if r["configuration_job_id"] == job["id"])
    approve = client.post(f"/api/v1/approval/requests/{request['id']}/approve", headers=approver_headers, json={})
    assert approve.status_code == 200, approve.text
    return job


def test_deployment_requires_approved_job(client, admin_headers, asset_type):
    job = client.post("/api/v1/configuration/jobs", headers=admin_headers, json={"name": "x", "justification_ref": "y"}).json()["data"]
    response = client.post("/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": job["id"]})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFIGURATION_JOB_NOT_APPROVED"


def test_deployment_precheck_fails_for_unreachable_asset(client, admin_headers, approver_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "dep-unreachable")  # no management_ip/credential
    job = _approved_job(client, admin_headers, approver_headers, asset, "Precheck fail job")

    create = client.post("/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": job["id"]})
    assert create.status_code == 201, create.text
    deployment = create.json()["data"]

    start = client.post(f"/api/v1/deployment/jobs/{deployment['id']}/start", headers=admin_headers)
    assert start.status_code == 200

    result = client.get(f"/api/v1/deployment/jobs/{deployment['id']}", headers=admin_headers).json()["data"]
    assert result["status"] == "precheck_failed"

    notifications = client.get("/api/v1/notifications", headers=admin_headers).json()["data"]
    assert any(n["type"] == "deployment_failed" and n["object_id"] == deployment["id"] for n in notifications)


def test_deployment_happy_path_with_fake_driver(client, admin_headers, approver_headers, asset_type, monkeypatch):
    asset = _create_reachable_asset(client, admin_headers, asset_type, "dep-happy")
    job = _approved_job(client, admin_headers, approver_headers, asset, "Happy path job")

    fake = FakeDriver(deploy_succeeds=True, verify_matches=True)
    monkeypatch.setattr("app.domains.deployment.service.get_driver", lambda tech: fake)
    monkeypatch.setattr("app.domains.backup.service.get_driver", lambda tech: fake)

    deployment = client.post("/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": job["id"]}).json()["data"]
    client.post(f"/api/v1/deployment/jobs/{deployment['id']}/start", headers=admin_headers)

    result = client.get(f"/api/v1/deployment/jobs/{deployment['id']}", headers=admin_headers).json()["data"]
    assert result["status"] == "success"

    results = client.get(f"/api/v1/deployment/jobs/{deployment['id']}/results", headers=admin_headers).json()["data"]
    assert len(results) == 1
    assert results[0]["success"] is True
    assert results[0]["verified"] is True

    events = client.get(f"/api/v1/deployment/jobs/{deployment['id']}/events", headers=admin_headers).json()["data"]
    event_types = [e["event_type"] for e in events]
    assert "backup_completed" in event_types
    assert "completed" in event_types

    backups = client.get(f"/api/v1/assets/{asset['id']}/backups", headers=admin_headers).json()["data"]
    assert any(b["backup_type"] == "pre_deployment" for b in backups)


def test_deployment_rolls_back_on_apply_failure(client, admin_headers, approver_headers, asset_type, monkeypatch):
    asset = _create_reachable_asset(client, admin_headers, asset_type, "dep-fail")
    job = _approved_job(client, admin_headers, approver_headers, asset, "Rollback job")

    fake = FakeDriver(deploy_succeeds=False)
    monkeypatch.setattr("app.domains.deployment.service.get_driver", lambda tech: fake)
    monkeypatch.setattr("app.domains.backup.service.get_driver", lambda tech: fake)

    deployment = client.post("/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": job["id"]}).json()["data"]
    client.post(f"/api/v1/deployment/jobs/{deployment['id']}/start", headers=admin_headers)

    result = client.get(f"/api/v1/deployment/jobs/{deployment['id']}", headers=admin_headers).json()["data"]
    assert result["status"] == "rolled_back"


def test_deployment_backup_connection_error_ends_at_backup_failed_not_a_crash(client, admin_headers, approver_headers, asset_type, monkeypatch, db_session):
    from app.domains.deployment.models import ResourceLock

    class ConnectRaisesDriver(FakeDriver):
        def connect(self, *, host, port, username, password=None, **kwargs):
            raise TimeoutError("device unreachable")

    asset = _create_reachable_asset(client, admin_headers, asset_type, "dep-backup-crash")
    job = _approved_job(client, admin_headers, approver_headers, asset, "Backup crash job")

    fake = ConnectRaisesDriver()
    monkeypatch.setattr("app.domains.deployment.service.get_driver", lambda tech: fake)
    monkeypatch.setattr("app.domains.backup.service.get_driver", lambda tech: fake)

    deployment = client.post("/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": job["id"]}).json()["data"]
    start = client.post(f"/api/v1/deployment/jobs/{deployment['id']}/start", headers=admin_headers)
    assert start.status_code == 200

    # A device connection failure while taking the pre-deployment backup must not crash the
    # whole run (which would silently roll back the deployment's status trail and its
    # resource lock via the worker) - it should land as an explicit backup failure.
    result = client.get(f"/api/v1/deployment/jobs/{deployment['id']}", headers=admin_headers).json()["data"]
    assert result["status"] == "backup_failed"

    remaining_locks = db_session.query(ResourceLock).filter(ResourceLock.deployment_job_id == deployment["id"]).all()
    assert remaining_locks == []


def test_deployment_verify_exception_ends_at_verify_failed_not_a_crash(client, admin_headers, approver_headers, asset_type, monkeypatch, db_session):
    from app.domains.deployment.models import ResourceLock

    class VerifyRaisesDriver(FakeDriver):
        def verify(self, object_type, parameters):
            raise ConnectionError("session dropped mid-verify")

    asset = _create_reachable_asset(client, admin_headers, asset_type, "dep-verify-crash")
    job = _approved_job(client, admin_headers, approver_headers, asset, "Verify crash job")

    fake = VerifyRaisesDriver(deploy_succeeds=True)
    monkeypatch.setattr("app.domains.deployment.service.get_driver", lambda tech: fake)
    monkeypatch.setattr("app.domains.backup.service.get_driver", lambda tech: fake)

    deployment = client.post("/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": job["id"]}).json()["data"]
    start = client.post(f"/api/v1/deployment/jobs/{deployment['id']}/start", headers=admin_headers)
    assert start.status_code == 200

    # A dropped verify session must not crash the whole run - the apply already happened, so
    # this should land as an explicit verify failure, not an exception that rolls back the
    # deployment's entire status trail while the live device has already been changed.
    result = client.get(f"/api/v1/deployment/jobs/{deployment['id']}", headers=admin_headers).json()["data"]
    assert result["status"] == "verify_failed"

    events = client.get(f"/api/v1/deployment/jobs/{deployment['id']}/events", headers=admin_headers).json()["data"]
    assert any(e["event_type"] == "verify_error" for e in events)

    remaining_locks = db_session.query(ResourceLock).filter(ResourceLock.deployment_job_id == deployment["id"]).all()
    assert remaining_locks == []


def test_deployment_lock_prevents_concurrent_deployment(client, admin_headers, approver_headers, asset_type, db_session):
    import datetime

    from app.domains.deployment.models import ResourceLock

    asset = _create_reachable_asset(client, admin_headers, asset_type, "dep-locked")
    job1 = _approved_job(client, admin_headers, approver_headers, asset, "Locked job 1")
    holder = client.post("/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": job1["id"]}).json()["data"]

    # Simulate a still-active lock from `holder`'s in-flight (but not yet started here) run.
    db_session.add(
        ResourceLock(
            asset_id=asset["id"],
            lock_type="deployment",
            deployment_job_id=holder["id"],
            locked_at=datetime.datetime.now(datetime.timezone.utc),
            expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10),
        )
    )
    db_session.commit()

    job2 = _approved_job(client, admin_headers, approver_headers, asset, "Locked job 2")
    deployment = client.post("/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": job2["id"]}).json()["data"]
    client.post(f"/api/v1/deployment/jobs/{deployment['id']}/start", headers=admin_headers)

    result = client.get(f"/api/v1/deployment/jobs/{deployment['id']}", headers=admin_headers).json()["data"]
    assert result["status"] == "precheck_failed"


def test_viewer_cannot_start_deployment(client, admin_headers, approver_headers, viewer_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "dep-denied")
    job = _approved_job(client, admin_headers, approver_headers, asset, "Denied job")
    deployment = client.post("/api/v1/deployment/jobs", headers=admin_headers, json={"configuration_job_id": job["id"]}).json()["data"]

    response = client.post(f"/api/v1/deployment/jobs/{deployment['id']}/start", headers=viewer_headers)
    assert response.status_code == 403
