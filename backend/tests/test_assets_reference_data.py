def test_vendor_create_and_list(client, admin_headers):
    create = client.post("/api/v1/vendors", headers=admin_headers, json={"name": "Cisco"})
    assert create.status_code == 201, create.text

    duplicate = client.post("/api/v1/vendors", headers=admin_headers, json={"name": "Cisco"})
    assert duplicate.status_code == 409

    listed = client.get("/api/v1/vendors", headers=admin_headers).json()["data"]
    assert any(v["name"] == "Cisco" for v in listed)


def test_location_create_and_list(client, admin_headers):
    create = client.post(
        "/api/v1/locations", headers=admin_headers, json={"name": "HQ Datacenter", "address": "123 Main St"}
    )
    assert create.status_code == 201, create.text
    body = create.json()["data"]
    assert body["name"] == "HQ Datacenter"
    assert body["address"] == "123 Main St"

    listed = client.get("/api/v1/locations", headers=admin_headers).json()["data"]
    assert any(loc["name"] == "HQ Datacenter" for loc in listed)


def test_zone_create_and_list(client, admin_headers):
    create = client.post(
        "/api/v1/zones", headers=admin_headers, json={"name": "DMZ", "description": "Perimeter network"}
    )
    assert create.status_code == 201, create.text

    duplicate = client.post("/api/v1/zones", headers=admin_headers, json={"name": "DMZ"})
    assert duplicate.status_code == 409

    listed = client.get("/api/v1/zones", headers=admin_headers).json()["data"]
    assert any(z["name"] == "DMZ" for z in listed)


def test_operating_system_create_and_list(client, admin_headers):
    vendor = client.post("/api/v1/vendors", headers=admin_headers, json={"name": "Microsoft"}).json()["data"]

    create = client.post(
        "/api/v1/operating-systems",
        headers=admin_headers,
        json={"name": "Windows Server 2022", "vendor_id": vendor["id"]},
    )
    assert create.status_code == 201, create.text

    duplicate = client.post(
        "/api/v1/operating-systems",
        headers=admin_headers,
        json={"name": "Windows Server 2022", "vendor_id": vendor["id"]},
    )
    assert duplicate.status_code == 409

    same_name_other_vendor = client.post(
        "/api/v1/operating-systems", headers=admin_headers, json={"name": "Windows Server 2022"}
    )
    assert same_name_other_vendor.status_code == 201, same_name_other_vendor.text

    listed = client.get("/api/v1/operating-systems", headers=admin_headers).json()["data"]
    assert any(o["name"] == "Windows Server 2022" and o["vendor_id"] == vendor["id"] for o in listed)


def test_operating_system_create_with_unknown_vendor_returns_404(client, admin_headers):
    response = client.post(
        "/api/v1/operating-systems",
        headers=admin_headers,
        json={"name": "Some OS", "vendor_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404
