import io

from app.domains.assets.models import ComplianceFramework


def _make_compliance_frameworks(db_session):
    iso = ComplianceFramework(code="iso27001", name="ISO/IEC 27001")
    pci = ComplianceFramework(code="pci_dss", name="PCI-DSS")
    db_session.add_all([iso, pci])
    db_session.commit()
    return iso, pci


def test_create_asset_with_isms_fields(client, admin_headers, asset_type, db_session):
    iso, pci = _make_compliance_frameworks(db_session)

    response = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={
            "name": "core-db-01",
            "asset_type_id": str(asset_type.id),
            "information_classification": "confidential",
            "compliance_framework_codes": ["iso27001", "pci_dss"],
            "acquired_at": "2024-01-15",
            "warranty_expires_at": "2027-01-15",
            "risk_assessment_ref": "RISK-2024-042",
            "risk_last_reviewed_at": "2026-06-01",
            "backup_required": True,
            "backup_frequency": "daily",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["information_classification"] == "confidential"
    assert sorted(body["compliance_scope"]) == ["iso27001", "pci_dss"]
    assert body["acquired_at"] == "2024-01-15"
    assert body["backup_required"] is True
    assert body["backup_frequency"] == "daily"


def test_create_asset_with_unknown_compliance_code_returns_404(client, admin_headers, asset_type):
    response = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={"name": "sw-x", "asset_type_id": str(asset_type.id), "compliance_framework_codes": ["nonexistent"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COMPLIANCE_FRAMEWORK_NOT_FOUND"


def test_update_asset_replaces_compliance_scope(client, admin_headers, asset_type, db_session):
    iso, pci = _make_compliance_frameworks(db_session)
    created = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={"name": "sw-y", "asset_type_id": str(asset_type.id), "compliance_framework_codes": ["iso27001"]},
    ).json()["data"]
    assert created["compliance_scope"] == ["iso27001"]

    updated = client.put(
        f"/api/v1/assets/{created['id']}", headers=admin_headers, json={"compliance_framework_codes": ["pci_dss"]}
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["compliance_scope"] == ["pci_dss"]


def test_default_information_classification_is_internal(client, admin_headers, asset_type):
    created = client.post(
        "/api/v1/assets", headers=admin_headers, json={"name": "sw-z", "asset_type_id": str(asset_type.id)}
    ).json()["data"]
    assert created["information_classification"] == "internal"
    assert created["backup_required"] is False
    assert created["compliance_scope"] == []


def test_list_compliance_frameworks(client, admin_headers, db_session):
    _make_compliance_frameworks(db_session)
    response = client.get("/api/v1/compliance-frameworks", headers=admin_headers)
    assert response.status_code == 200
    codes = {f["code"] for f in response.json()["data"]}
    assert {"iso27001", "pci_dss"}.issubset(codes)


def test_export_assets_csv_contains_isms_columns(client, admin_headers, asset_type, db_session):
    _make_compliance_frameworks(db_session)
    client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={
            "name": "export-test-01",
            "asset_type_id": str(asset_type.id),
            "information_classification": "restricted",
            "compliance_framework_codes": ["iso27001"],
            "criticality": "high",
        },
    )

    response = client.get("/api/v1/assets/export/csv", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    assert "information_classification" in body.splitlines()[0]
    assert "export-test-01" in body
    assert "restricted" in body
    assert "iso27001" in body


def test_import_assets_csv_creates_and_updates(client, admin_headers, asset_type, db_session):
    _make_compliance_frameworks(db_session)
    csv_content = (
        "name,asset_type_code,criticality,information_classification,compliance_scope\n"
        "csv-created-01,router,high,confidential,iso27001;pci_dss\n"
    )
    files = {"file": ("assets.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    response = client.post("/api/v1/assets/import/csv", headers=admin_headers, files=files)
    assert response.status_code == 200, response.text
    summary = response.json()["data"]
    assert summary["created"] == 1
    assert summary["updated"] == 0
    assert summary["errors"] == []

    listing = client.get("/api/v1/assets", headers=admin_headers, params={"search": "csv-created-01"}).json()["data"]
    assert len(listing) == 1
    assert listing[0]["criticality"] == "high"
    assert listing[0]["information_classification"] == "confidential"
    assert sorted(listing[0]["compliance_scope"]) == ["iso27001", "pci_dss"]
    asset_code = listing[0]["asset_code"]

    # Re-import with the same asset_code and a changed field - must update, not duplicate.
    csv_content_update = (
        f"asset_code,name,asset_type_code,criticality\n{asset_code},csv-created-01,router,critical\n"
    )
    files = {"file": ("assets2.csv", io.BytesIO(csv_content_update.encode()), "text/csv")}
    response2 = client.post("/api/v1/assets/import/csv", headers=admin_headers, files=files)
    summary2 = response2.json()["data"]
    assert summary2["created"] == 0
    assert summary2["updated"] == 1

    all_assets = client.get("/api/v1/assets", headers=admin_headers, params={"search": "csv-created-01"}).json()["data"]
    assert len(all_assets) == 1
    assert all_assets[0]["criticality"] == "critical"


def test_import_assets_csv_bad_row_does_not_crash_whole_batch(client, admin_headers, asset_type):
    csv_content = (
        "name,asset_type_code,criticality\n"
        "good-row,router,high\n"
        "bad-row,router,not-a-real-criticality\n"
        "another-good-row,router,low\n"
    )
    files = {"file": ("assets.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    response = client.post("/api/v1/assets/import/csv", headers=admin_headers, files=files)
    assert response.status_code == 200, response.text
    summary = response.json()["data"]
    assert summary["created"] == 2
    assert len(summary["errors"]) == 1
    assert summary["errors"][0]["row"] == 3
    assert "criticality" in summary["errors"][0]["message"]


def test_import_assets_csv_unknown_asset_type_reports_row_error(client, admin_headers):
    csv_content = "name,asset_type_code\nsome-device,does_not_exist\n"
    files = {"file": ("assets.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    response = client.post("/api/v1/assets/import/csv", headers=admin_headers, files=files)
    summary = response.json()["data"]
    assert summary["created"] == 0
    assert len(summary["errors"]) == 1
    assert "does_not_exist" in summary["errors"][0]["message"]


def test_viewer_cannot_import_csv(client, viewer_headers):
    csv_content = "name,asset_type_code\nx,router\n"
    files = {"file": ("assets.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    response = client.post("/api/v1/assets/import/csv", headers=viewer_headers, files=files)
    assert response.status_code == 403


def test_viewer_can_export_csv(client, viewer_headers):
    response = client.get("/api/v1/assets/export/csv", headers=viewer_headers)
    assert response.status_code == 200
