def test_manual_discovery_creates_asset(client, admin_headers, asset_type):
    response = client.post(
        "/api/v1/discovery/jobs",
        headers=admin_headers,
        json={
            "method": "manual",
            "scope": {
                "records": [
                    {"name": "disc-sw-1", "asset_type_code": asset_type.code, "management_ip": "10.1.1.1"}
                ]
            },
        },
    )
    assert response.status_code == 201, response.text
    job = response.json()["data"]
    assert job["status"] == "success"
    assert job["discovered_count"] == 1

    assets = client.get("/api/v1/assets?search=disc-sw-1", headers=admin_headers).json()["data"]
    assert len(assets) == 1
    assert assets[0]["management_ip"] == "10.1.1.1"
    assert assets[0]["discovery_source"] == "manual"


def test_manual_discovery_rerun_updates_existing_asset(client, admin_headers, asset_type):
    payload = {
        "method": "manual",
        "scope": {
            "records": [{"name": "disc-sw-2", "asset_type_code": asset_type.code, "management_ip": "10.1.1.2"}]
        },
    }
    first = client.post("/api/v1/discovery/jobs", headers=admin_headers, json=payload).json()["data"]
    assert first["discovered_count"] == 1

    second = client.post("/api/v1/discovery/jobs", headers=admin_headers, json=payload).json()["data"]
    assert second["updated_count"] == 1
    assert second["discovered_count"] == 0

    assets = client.get("/api/v1/assets?search=disc-sw-2", headers=admin_headers).json()["data"]
    assert len(assets) == 1


def test_csv_import_creates_multiple_assets(client, admin_headers, asset_type):
    csv_content = (
        "name,asset_type_code,management_ip\n"
        f"disc-csv-1,{asset_type.code},10.1.2.1\n"
        f"disc-csv-2,{asset_type.code},10.1.2.2\n"
    )
    response = client.post(
        "/api/v1/discovery/jobs",
        headers=admin_headers,
        json={"method": "csv_import", "scope": {"csv_content": csv_content}},
    )
    assert response.status_code == 201
    job = response.json()["data"]
    assert job["status"] == "success"
    assert job["discovered_count"] == 2


def test_csv_import_ragged_row_recorded_as_error_not_a_crash(client, admin_headers, asset_type):
    # The second data row has an extra, unheaded column - csv.DictReader files that under
    # key None as a list rather than raising, and it must not crash the whole import.
    csv_content = (
        "name,asset_type_code,management_ip\n"
        f"disc-csv-good,{asset_type.code},10.1.2.1\n"
        f"disc-csv-ragged,{asset_type.code},10.1.2.2,extra-column\n"
    )
    response = client.post(
        "/api/v1/discovery/jobs",
        headers=admin_headers,
        json={"method": "csv_import", "scope": {"csv_content": csv_content}},
    )
    assert response.status_code == 201
    job = response.json()["data"]
    assert job["status"] == "partial"
    assert job["discovered_count"] == 1
    assert job["failed_count"] == 1

    errors = client.get(f"/api/v1/discovery/jobs/{job['id']}/errors", headers=admin_headers).json()["data"]
    assert any("more columns than the header" in e["message"] for e in errors)


def test_discovery_unknown_asset_type_is_recorded_as_error(client, admin_headers):
    response = client.post(
        "/api/v1/discovery/jobs",
        headers=admin_headers,
        json={"method": "manual", "scope": {"records": [{"name": "bad", "asset_type_code": "does-not-exist"}]}},
    )
    job = response.json()["data"]
    assert job["status"] == "failed"
    assert job["failed_count"] == 1

    errors = client.get(f"/api/v1/discovery/jobs/{job['id']}/errors", headers=admin_headers).json()["data"]
    assert len(errors) == 1
    assert "does-not-exist" in errors[0]["message"]


def test_unimplemented_discovery_method_fails_cleanly(client, admin_headers):
    response = client.post("/api/v1/discovery/jobs", headers=admin_headers, json={"method": "snmp", "scope": {}})
    job = response.json()["data"]
    assert job["status"] == "failed"

    errors = client.get(f"/api/v1/discovery/jobs/{job['id']}/errors", headers=admin_headers).json()["data"]
    assert "not implemented" in errors[0]["message"]


def test_viewer_cannot_create_discovery_job(client, viewer_headers):
    response = client.post("/api/v1/discovery/jobs", headers=viewer_headers, json={"method": "manual", "scope": {}})
    assert response.status_code == 403


def test_discovery_job_cancel(client, admin_headers):
    create = client.post("/api/v1/discovery/jobs", headers=admin_headers, json={"method": "manual", "scope": {}})
    job_id = create.json()["data"]["id"]
    # Already SUCCESS since manual with no records completes synchronously; cancel is a no-op then.
    cancel = client.post(f"/api/v1/discovery/jobs/{job_id}/cancel", headers=admin_headers)
    assert cancel.status_code == 200
