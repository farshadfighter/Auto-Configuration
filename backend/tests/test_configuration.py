def _create_asset(client, headers, asset_type, name, **extra):
    payload = {"name": name, "asset_type_id": str(asset_type.id), **extra}
    response = client.post("/api/v1/assets", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_manual_job_requires_justification(client, admin_headers):
    response = client.post("/api/v1/configuration/jobs", headers=admin_headers, json={"name": "No justification"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "JUSTIFICATION_REQUIRED"


def test_design_job_requires_source_version(client, admin_headers):
    response = client.post(
        "/api/v1/configuration/jobs", headers=admin_headers, json={"name": "x", "source_type": "design"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SOURCE_DESIGN_VERSION_REQUIRED"


def _create_job(client, headers, name="Add branch VLAN"):
    response = client.post(
        "/api/v1/configuration/jobs",
        headers=headers,
        json={"name": name, "justification_ref": "TICKET-123"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_full_generate_validate_diff_flow(client, admin_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "cfg-switch-1", management_ip="10.9.9.1")
    job = _create_job(client, admin_headers)
    assert job["job_number"].startswith("CFG-")

    obj = client.post(
        f"/api/v1/configuration/jobs/{job['id']}/objects",
        headers=admin_headers,
        json={
            "asset_id": asset["id"],
            "technology": "cisco_iosxe",
            "object_type": "vlan",
            "parameters": {"vlan_id": 120, "name": "Guest"},
        },
    )
    assert obj.status_code == 201, obj.text

    generate = client.post(f"/api/v1/configuration/jobs/{job['id']}/generate", headers=admin_headers)
    assert generate.status_code == 200, generate.text
    assert generate.json()["data"]["status"] == "generated"

    objects = client.get(f"/api/v1/configuration/jobs/{job['id']}/objects", headers=admin_headers).json()["data"]
    assert objects[0]["change_type"] == "create"
    assert "vlan 120" in objects[0]["rendered_operations"][0]["rendered_config"]

    validate = client.post(f"/api/v1/configuration/jobs/{job['id']}/validate", headers=admin_headers)
    assert validate.status_code == 200, validate.text
    assert validate.json()["data"]["status"] == "validated"
    assert validate.json()["data"]["risk_level"] == "low"

    diff = client.get(f"/api/v1/configuration/jobs/{job['id']}/diff", headers=admin_headers).json()["data"]
    assert diff[0]["change_type"] == "create"
    assert diff[0]["current_state"] is None

    submit = client.post(f"/api/v1/configuration/jobs/{job['id']}/submit-approval", headers=admin_headers)
    assert submit.status_code == 200
    assert submit.json()["data"]["status"] == "pending_approval"


def test_generate_fails_before_objects_added(client, admin_headers):
    job = _create_job(client, admin_headers)
    response = client.post(f"/api/v1/configuration/jobs/{job['id']}/generate", headers=admin_headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_OBJECTS"


def test_invalid_vlan_blocks_job_with_critical_validation(client, admin_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "cfg-switch-invalid")
    job = _create_job(client, admin_headers)
    client.post(
        f"/api/v1/configuration/jobs/{job['id']}/objects",
        headers=admin_headers,
        json={
            "asset_id": asset["id"],
            "technology": "cisco_iosxe",
            "object_type": "vlan",
            "parameters": {"vlan_id": 9999, "name": "Bad"},
        },
    )
    client.post(f"/api/v1/configuration/jobs/{job['id']}/generate", headers=admin_headers)
    validate = client.post(f"/api/v1/configuration/jobs/{job['id']}/validate", headers=admin_headers)
    assert validate.json()["data"]["status"] == "failed"

    objects = client.get(f"/api/v1/configuration/jobs/{job['id']}/objects", headers=admin_headers).json()["data"]
    assert objects[0]["validation_status"] == "critical"

    submit = client.post(f"/api/v1/configuration/jobs/{job['id']}/submit-approval", headers=admin_headers)
    assert submit.status_code == 409  # can't submit a FAILED job


def test_dependency_cycle_fails_job(client, admin_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "cfg-switch-cycle")
    job = _create_job(client, admin_headers)
    obj_a = client.post(
        f"/api/v1/configuration/jobs/{job['id']}/objects",
        headers=admin_headers,
        json={"asset_id": asset["id"], "technology": "cisco_iosxe", "object_type": "vlan", "parameters": {"vlan_id": 10, "name": "A"}},
    ).json()["data"]
    obj_b = client.post(
        f"/api/v1/configuration/jobs/{job['id']}/objects",
        headers=admin_headers,
        json={"asset_id": asset["id"], "technology": "cisco_iosxe", "object_type": "vlan", "parameters": {"vlan_id": 11, "name": "B"}},
    ).json()["data"]

    client.post(
        f"/api/v1/configuration/jobs/{job['id']}/dependencies",
        headers=admin_headers,
        json={"parent_object_id": obj_a["id"], "child_object_id": obj_b["id"]},
    )
    client.post(
        f"/api/v1/configuration/jobs/{job['id']}/dependencies",
        headers=admin_headers,
        json={"parent_object_id": obj_b["id"], "child_object_id": obj_a["id"]},
    )

    generate = client.post(f"/api/v1/configuration/jobs/{job['id']}/generate", headers=admin_headers)
    assert generate.status_code == 409
    assert generate.json()["error"]["code"] == "DEPENDENCY_CYCLE"

    job_after = client.get(f"/api/v1/configuration/jobs/{job['id']}", headers=admin_headers).json()["data"]
    assert job_after["status"] == "failed"


def test_dependency_order_respected_in_execution_order(client, admin_headers, asset_type):
    asset = _create_asset(client, admin_headers, asset_type, "cfg-switch-order")
    job = _create_job(client, admin_headers)
    vlan_obj = client.post(
        f"/api/v1/configuration/jobs/{job['id']}/objects",
        headers=admin_headers,
        json={"asset_id": asset["id"], "technology": "cisco_iosxe", "object_type": "vlan", "parameters": {"vlan_id": 50, "name": "Data"}},
    ).json()["data"]
    interface_obj = client.post(
        f"/api/v1/configuration/jobs/{job['id']}/objects",
        headers=admin_headers,
        json={
            "asset_id": asset["id"],
            "technology": "cisco_iosxe",
            "object_type": "interface",
            "parameters": {"name": "Gi1/0/1", "mode": "access", "access_vlan": 50},
        },
    ).json()["data"]
    # interface depends on vlan existing first
    client.post(
        f"/api/v1/configuration/jobs/{job['id']}/dependencies",
        headers=admin_headers,
        json={"parent_object_id": vlan_obj["id"], "child_object_id": interface_obj["id"]},
    )

    client.post(f"/api/v1/configuration/jobs/{job['id']}/generate", headers=admin_headers)
    objects = {o["id"]: o for o in client.get(f"/api/v1/configuration/jobs/{job['id']}/objects", headers=admin_headers).json()["data"]}
    assert objects[vlan_obj["id"]]["execution_order"] < objects[interface_obj["id"]]["execution_order"]


def test_viewer_cannot_create_job(client, viewer_headers):
    response = client.post("/api/v1/configuration/jobs", headers=viewer_headers, json={"name": "x", "justification_ref": "y"})
    assert response.status_code == 403


def test_technology_catalog(client, admin_headers):
    response = client.get("/api/v1/technologies", headers=admin_headers)
    assert response.status_code == 200
    technologies = {t["technology"] for t in response.json()["data"]}
    assert {"cisco_iosxe", "fortios", "windows_dns", "windows_dhcp"}.issubset(technologies)


def test_profile_lifecycle(client, admin_headers):
    create = client.post(
        "/api/v1/configuration/profiles",
        headers=admin_headers,
        json={
            "name": "Secure Access Switch",
            "technology": "cisco_iosxe",
            "object_type": "interface",
            "parameters_template": {"mode": "access"},
        },
    )
    assert create.status_code == 201
    profile = create.json()["data"]
    assert profile["status"] == "draft"

    update = client.put(
        f"/api/v1/configuration/profiles/{profile['id']}",
        headers=admin_headers,
        json={"parameters_template": {"mode": "access", "portfast": True}},
    )
    assert update.status_code == 200

    publish = client.post(f"/api/v1/configuration/profiles/{profile['id']}/publish", headers=admin_headers)
    assert publish.status_code == 200
    assert publish.json()["data"]["status"] == "published"

    blocked = client.put(
        f"/api/v1/configuration/profiles/{profile['id']}", headers=admin_headers, json={"description": "nope"}
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "PROFILE_NOT_EDITABLE"

    new_version = client.post(f"/api/v1/configuration/profiles/{profile['id']}/versions", headers=admin_headers)
    assert new_version.status_code == 201
    assert new_version.json()["data"]["version"] == 2
    assert new_version.json()["data"]["status"] == "draft"
