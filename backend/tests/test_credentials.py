def test_credential_secret_is_never_returned(client, admin_headers):
    response = client.post(
        "/api/v1/credentials",
        headers=admin_headers,
        json={
            "name": "cisco-lab",
            "credential_type": "username_password",
            "username": "admin",
            "secrets": {"password": "S3cretPass!"},
        },
    )
    assert response.status_code == 201
    body = response.json()["data"]
    assert body["secret_keys"] == ["password"]
    assert "password" not in body
    assert "S3cretPass!" not in response.text


def test_credential_secret_roundtrips_through_encryption(client, admin_headers, db_session):
    create = client.post(
        "/api/v1/credentials",
        headers=admin_headers,
        json={
            "name": "cisco-lab-2",
            "credential_type": "username_password",
            "username": "admin",
            "secrets": {"password": "S3cretPass!"},
        },
    )
    profile_id = create.json()["data"]["id"]

    from app.domains.credentials.service import resolve_secret

    assert resolve_secret(db_session, profile_id, "password") == "S3cretPass!"


def test_credential_secret_rotation(client, admin_headers, db_session):
    create = client.post(
        "/api/v1/credentials",
        headers=admin_headers,
        json={
            "name": "cisco-lab-3",
            "credential_type": "username_password",
            "username": "admin",
            "secrets": {"password": "OldPass!"},
        },
    )
    profile_id = create.json()["data"]["id"]

    rotate = client.put(
        f"/api/v1/credentials/{profile_id}", headers=admin_headers, json={"secrets": {"password": "NewPass!"}}
    )
    assert rotate.status_code == 200

    from app.domains.credentials.service import resolve_secret

    assert resolve_secret(db_session, profile_id, "password") == "NewPass!"
