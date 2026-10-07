from __future__ import annotations

from tests.conftest import OTHER_PASSWORD, login


def test_requires_authentication(client):
    response = client.get("/api/v1/dealers")
    assert response.status_code == 401 and response.json() == {"message": "Not authenticated."}


def test_tenant_isolation(client):
    login(client, "omar@other.example", OTHER_PASSWORD)
    assert client.get("/api/v1/dealers").json()["total"] == 0
    assert client.get("/api/v1/dealers/DLR-1001").status_code == 404
    assert client.get("/api/v1/communications").json()["total"] == 0
    assert client.get("/api/v1/sales/uploads").json() == []
    assert client.get("/api/v1/sales/analytics").json()["hasData"] is False
    blocked = client.post("/api/v1/dealers/DLR-1001/messages", data={"subject": "Hello", "message": "Cross-tenant attempt"})
    assert blocked.status_code == 404


def test_profile_and_settings(auth_client):
    me = auth_client.get("/api/v1/users/me").json()
    assert me["id"] == "USR-2001"
    updated = auth_client.patch(
        "/api/v1/users/me", json={"name": " John Smith ", "jobTitle": "VP Channel Sales", "phone": "+91 98110 45512"}
    )
    assert updated.status_code == 200 and updated.json()["jobTitle"] == "VP Channel Sales"
    assert auth_client.patch("/api/v1/users/me", json={"name": "J", "phone": "abc"}).status_code == 422
    auth_client.patch(
        "/api/v1/users/me", json={"name": "John Smith", "jobTitle": "Head of Channel Sales", "phone": "+91 98110 45512"}
    )

    assert auth_client.get("/api/v1/users/me/settings").json() == {
        "defaultPageSize": 20,
        "applyFiltersInstantly": True,
        "desktopDealerView": "table",
    }
    assert (
        auth_client.put(
            "/api/v1/users/me/settings", json={"defaultPageSize": 25, "applyFiltersInstantly": True, "desktopDealerView": "table"}
        ).status_code
        == 422
    )
    saved = auth_client.put(
        "/api/v1/users/me/settings", json={"defaultPageSize": 50, "applyFiltersInstantly": False, "desktopDealerView": "cards"}
    ).json()
    assert saved == {"defaultPageSize": 50, "applyFiltersInstantly": False, "desktopDealerView": "cards"}
    assert auth_client.get("/api/v1/users/me/settings").json() == saved


def test_health_and_security_headers(client):
    response = client.get("/health")
    assert response.json() == {"status": "ok", "database": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert client.get("/api/v1/auth/session").headers["Cache-Control"] == "no-store"
