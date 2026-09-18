def test_asset_inventory_report_json_default(client, admin_headers):
    response = client.get("/api/v1/reports/asset-inventory", headers=admin_headers)
    assert response.status_code == 200
    assert "total" in response.json()["data"]


def test_asset_inventory_report_csv_export(client, admin_headers, asset_type):
    client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={"name": "csv-report-asset", "asset_type_id": str(asset_type.id), "managed": "managed"},
    )
    response = client.get("/api/v1/reports/asset-inventory", headers=admin_headers, params={"format": "csv"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=asset_inventory_report.csv" in response.headers["content-disposition"]
    body = response.text
    assert body.splitlines()[0] == "metric,value"
    assert "total," in body
    assert "by_managed.managed," in body


def test_technology_coverage_report_csv_export_is_a_table(client, admin_headers):
    response = client.get("/api/v1/reports/technology-coverage", headers=admin_headers, params={"format": "csv"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    header = response.text.splitlines()[0]
    assert header == "technology,vendor,object_types,deployed_asset_count"


def test_viewer_can_view_reports(client, viewer_headers):
    response = client.get("/api/v1/reports/drift", headers=viewer_headers)
    assert response.status_code == 200
