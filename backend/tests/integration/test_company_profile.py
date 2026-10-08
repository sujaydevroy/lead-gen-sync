"""A company's own user edits the company profile (PUT /companies/me)."""

from __future__ import annotations

from tests.conftest import VIEWER_PASSWORD, login


def test_company_admin_edits_own_company(auth_client):
    original = auth_client.get("/api/v1/companies/me").json()
    options = auth_client.get("/api/v1/companies/me/options").json()
    assert "Electrical & Electrical Equipment" in options["sectors"] and "India" in options["countries"]
    assert options["regions"][:2] == ["North", "South"]

    payload = {
        "name": "ABC Corporation Ltd",
        "logoText": "",
        "industry": "Electrical Equipment Manufacturing",
        "sector": "Electrical & Electrical Equipment",
        "website": "https://www.abc-corp.example",
        "email": "info@abc-corp.example",
        "phone": "+91 11 4000 1234",
        "addressLine1": "Plot 7, Industrial Area",
        "city": "Gurugram",
        "state": "Haryana",
        "postalCode": "122001",
        "country": "india",
        "region": "North",
        "registrationNumber": "U31900DL2001PLC000001",
        "taxId": "07AABCA1234A1Z5",
        "employees": 1250,
        "founded": 2001,
    }
    response = auth_client.put("/api/v1/companies/me", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == original["id"] and body["name"] == "ABC Corporation Ltd" and body["logoText"] == "ACL"
    assert body["address"]["city"] == "Gurugram" and body["address"]["country"] == "India" and body["employees"] == 1250
    assert auth_client.get("/api/v1/companies/me").json()["name"] == "ABC Corporation Ltd"
    assert auth_client.get("/api/v1/companies/me/sector").json()["sector"] == "Electrical & Electrical Equipment"

    bad = auth_client.put("/api/v1/companies/me", json={**payload, "sector": "Nope"})
    assert bad.status_code == 422 and "sector" in bad.json()["message"]
    assert auth_client.put("/api/v1/companies/me", json={**payload, "name": "A"}).status_code == 422

    # Put the seeded profile back for the other tests.
    restore = {
        "name": original["name"],
        "logoText": original["logoText"],
        "industry": original["industry"],
        "sector": original["sector"],
        "website": original["website"],
        "email": original["email"],
        "phone": original["phone"],
        "addressLine1": original["address"]["line1"],
        "city": original["address"]["city"],
        "state": original["address"]["state"],
        "postalCode": original["address"]["postalCode"],
        "country": original["address"]["country"],
        "region": original["address"]["region"],
        "registrationNumber": original["registrationNumber"],
        "taxId": original["taxId"],
        "employees": original["employees"],
        "founded": int(original["founded"]) if original["founded"] else None,
    }
    assert auth_client.put("/api/v1/companies/me", json=restore).json() == original


def test_only_company_administrators_edit_the_company(client):
    login(client, "vera.viewer@abc.com", VIEWER_PASSWORD)
    assert client.get("/api/v1/companies/me/options").status_code == 200
    assert client.put("/api/v1/companies/me", json={"name": "Hijacked"}).status_code == 403
