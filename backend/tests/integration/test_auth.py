from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import DEMO_PASSWORD, login
from tests.integration.helpers import make_user


def test_login_sets_cookies_and_returns_session_shape(client):
    body = login(client, remember=True)
    assert body["user"] == {
        "id": "USR-2001",
        "name": "John Smith",
        "email": "john.smith@abc.com",
        "role": "Company Administrator",
        "jobTitle": "Head of Channel Sales",
        "phone": "+91 98110 45512",
        "companyId": "CMP-10045",
        "country": "India",
        "region": "North",
    }
    assert body["expiresAt"]
    assert {"dcp_access", "dcp_refresh", "dcp_csrf"} <= set(client.cookies.keys())
    assert client.get("/api/v1/auth/session").json()["user"]["id"] == "USR-2001"


def test_invalid_login_is_generic(client):
    wrong = client.post("/api/v1/auth/login", json={"email": "john.smith@abc.com", "password": "nope"})
    unknown = client.post("/api/v1/auth/login", json={"email": "nobody@abc.com", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"message": "Invalid email or password."}


def test_session_is_null_when_signed_out(client):
    assert client.get("/api/v1/auth/session").json() == {"user": None, "expiresAt": None}


def test_logout_revokes_session(auth_client):
    assert auth_client.post("/api/v1/auth/logout").status_code == 200
    assert auth_client.get("/api/v1/auth/session").json()["user"] is None
    assert auth_client.get("/api/v1/users/me").status_code == 401


def test_lockout_after_repeated_failures(client):
    make_user("lockout@abc.com", "Correct-Password-1")
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json={"email": "lockout@abc.com", "password": "bad"}).status_code == 401
    locked = client.post("/api/v1/auth/login", json={"email": "lockout@abc.com", "password": "Correct-Password-1"})
    assert locked.status_code == 423
    assert "Too many failed attempts" in locked.json()["message"]


def test_refresh_rotation_and_reuse_detection(client):
    login(client)
    old_refresh = client.cookies.get("dcp_refresh")
    rotated = client.post("/api/v1/auth/refresh")
    assert rotated.status_code == 200
    new_refresh = client.cookies.get("dcp_refresh")
    assert new_refresh and new_refresh != old_refresh

    # Replaying the old (rotated) token is treated as theft: every session of the user is revoked.
    with TestClient(app) as attacker:
        replay = attacker.post("/api/v1/auth/refresh", headers={"Cookie": f"dcp_refresh={old_refresh}"})
        assert replay.status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_session_endpoint_refreshes_expired_access_token(client):
    login(client)
    client.cookies.delete("dcp_access")
    body = client.get("/api/v1/auth/session").json()
    assert body["user"]["id"] == "USR-2001"
    assert client.cookies.get("dcp_access")


def test_password_reset_flow(client, monkeypatch):
    make_user("reset@abc.com", "Original-Password-1")
    sent = []

    class Capture:
        def send(self, to, subject, body):
            sent.append((to, body))

    monkeypatch.setattr("app.services.auth_service.get_email_sender", lambda: Capture())
    assert client.post("/api/v1/auth/forgot-password", json={"email": "unknown@abc.com"}).status_code == 202
    assert client.post("/api/v1/auth/forgot-password", json={"email": "reset@abc.com"}).status_code == 202
    assert len(sent) == 1 and sent[0][0] == "reset@abc.com"
    token = sent[0][1].split("token=")[1].split()[0]

    weak = client.post("/api/v1/auth/reset-password", json={"token": token, "newPassword": "short"})
    assert weak.status_code == 422
    ok = client.post("/api/v1/auth/reset-password", json={"token": token, "newPassword": "Brand-New-Password-2"})
    assert ok.status_code == 200
    reused = client.post("/api/v1/auth/reset-password", json={"token": token, "newPassword": "Another-Password-3"})
    assert reused.status_code == 400
    assert (
        client.post("/api/v1/auth/login", json={"email": "reset@abc.com", "password": "Brand-New-Password-2"}).status_code == 200
    )


def test_bearer_token_flow_for_api_clients(client):
    token = client.post("/api/v1/auth/token", data={"username": "john.smith@abc.com", "password": DEMO_PASSWORD})
    assert token.status_code == 200
    headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
    with TestClient(app) as api_client:
        assert api_client.get("/api/v1/users/me", headers=headers).json()["id"] == "USR-2001"
        # Bearer-authenticated writes don't need the CSRF header.
        settings = api_client.put(
            "/api/v1/users/me/settings",
            headers=headers,
            json={"defaultPageSize": 20, "applyFiltersInstantly": True, "desktopDealerView": "table"},
        )
        assert settings.status_code == 200
        assert api_client.get("/api/v1/users/me", headers={"Authorization": "Bearer tampered.token.value"}).status_code == 401
