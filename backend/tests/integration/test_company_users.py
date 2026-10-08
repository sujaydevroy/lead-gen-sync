"""Company Administrators manage the users of their own company (add, role, activate / deactivate, unlock, password)."""

from __future__ import annotations

from tests.conftest import DEMO_PASSWORD, OTHER_PASSWORD, SYSADMIN_EMAIL, SYSADMIN_PASSWORD, VIEWER_PASSWORD, login

TEMP_PASSWORD = "Welcome-Temp-2026"


def sign_in(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_only_company_administrators_manage_users(client):
    login(client, "vera.viewer@abc.com", VIEWER_PASSWORD)
    assert client.get("/api/v1/users").status_code == 403
    assert client.post("/api/v1/users", json={}).status_code in (403, 422)
    login(client, "omar@other.example", OTHER_PASSWORD)  # Viewer of another company
    assert client.get("/api/v1/users").status_code == 403
    login(client, SYSADMIN_EMAIL, SYSADMIN_PASSWORD)  # system admins do not manage company users
    assert client.get("/api/v1/users").status_code == 403


def test_add_change_role_deactivate_and_reset(client):
    login(client)  # john.smith@abc.com, Company Administrator of CMP-10045
    roles = client.get("/api/v1/users/roles").json()
    assert roles == ["Company Administrator", "Sales Manager", "Sales Representative", "Viewer"]
    emails = [u["email"] for u in client.get("/api/v1/users").json()]
    assert "john.smith@abc.com" in emails and "omar@other.example" not in emails

    payload = {"name": "Priya Patel", "email": "priya.patel@abc.com", "jobTitle": "Sales Lead", "role": "Sales Manager",
               "password": TEMP_PASSWORD}  # fmt: skip
    created = client.post("/api/v1/users", json=payload)
    assert created.status_code == 201, created.text
    priya = created.json()
    assert priya["role"] == "Sales Manager" and priya["isActive"] is True and priya["country"] == "India"
    code = priya["id"]
    assert client.post("/api/v1/users", json={**payload, "email": "PRIYA.patel@abc.com"}).status_code == 409
    assert client.post("/api/v1/users", json={**payload, "email": "x@abc.com", "role": "System Administrator"}).status_code == 422

    assert client.patch(f"/api/v1/users/{code}", json={"role": "Viewer"}).json()["role"] == "Viewer"
    assert client.patch(f"/api/v1/users/{code}", json={"role": "Owner"}).status_code == 422

    # The new user signs in with the temporary password and changes it.
    login(client, "priya.patel@abc.com", TEMP_PASSWORD)
    wrong = client.post("/api/v1/users/me/password", json={"currentPassword": "nope", "newPassword": "Priya-Own-2026"})
    assert wrong.status_code == 400
    changed = client.post("/api/v1/users/me/password", json={"currentPassword": TEMP_PASSWORD, "newPassword": "Priya-Own-2026"})
    assert changed.status_code == 200
    assert sign_in(client, "priya.patel@abc.com", "Priya-Own-2026").status_code == 200

    login(client)
    assert client.patch(f"/api/v1/users/{code}", json={"isActive": False}).json()["isActive"] is False
    assert sign_in(client, "priya.patel@abc.com", "Priya-Own-2026").status_code == 401
    login(client)
    assert client.patch(f"/api/v1/users/{code}", json={"isActive": True}).json()["isActive"] is True

    # Lock the account with failed logins, then unlock it and set a new temporary password.
    for _ in range(6):
        sign_in(client, "priya.patel@abc.com", "wrong-password")
    login(client)
    locked = next(u for u in client.get("/api/v1/users").json() if u["id"] == code)
    assert locked["isLocked"] is True
    assert client.post(f"/api/v1/users/{code}/unlock").json()["isLocked"] is False
    assert client.post(f"/api/v1/users/{code}/password", json={"password": "short"}).status_code == 422
    assert client.post(f"/api/v1/users/{code}/password", json={"password": "Reset-Temp-2026"}).status_code == 200
    assert sign_in(client, "priya.patel@abc.com", "Reset-Temp-2026").status_code == 200


def test_admin_cannot_lock_themselves_out_or_touch_other_companies(client):
    login(client)
    me = client.get("/api/v1/users/me").json()["id"]
    assert client.patch(f"/api/v1/users/{me}", json={"isActive": False}).status_code == 409
    assert client.patch(f"/api/v1/users/{me}", json={"role": "Viewer"}).status_code == 409
    assert client.patch(f"/api/v1/users/{me}", json={"role": "Company Administrator", "isActive": True}).status_code == 200
    assert client.patch("/api/v1/users/USR-3001", json={"isActive": False}).status_code == 404  # Omar, other company
    assert client.post("/api/v1/users/USR-9001/password", json={"password": "Hijack-Pass-2026"}).status_code == 404
    assert sign_in(client, "john.smith@abc.com", DEMO_PASSWORD).status_code == 200
