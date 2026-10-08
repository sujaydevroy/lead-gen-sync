"""System administrators: companies (CRUD + read-only users) and dealer file uploads."""

from __future__ import annotations

import io
import json
from pathlib import Path

from openpyxl import Workbook, load_workbook

from tests.conftest import DEMO_PASSWORD, SYSADMIN_EMAIL, SYSADMIN_PASSWORD, VIEWER_PASSWORD, login

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
NEW_ADMIN_PASSWORD = "Northwind-Admin-2026"


def sysadmin(client):
    login(client, SYSADMIN_EMAIL, SYSADMIN_PASSWORD)
    return client


def new_company(client, name: str, email: str, **fields) -> dict:
    payload = {
        "name": name,
        "industry": "Electrical Equipment",
        "sector": "Electrical & Electrical Equipment",
        "country": "India",
        "region": "West",
        "email": "",
        "admin": {"name": f"{name} Admin", "email": email, "password": NEW_ADMIN_PASSWORD},
        **fields,
    }
    response = client.post("/api/v1/admin/companies", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def xlsx(rows: list[list]) -> bytes:
    book = Workbook()
    for row in rows:
        book.active.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def upload(client, company_id: str, content: bytes, name: str):
    return client.post("/api/v1/admin/dealer-uploads", data={"companyId": company_id}, files={"file": (name, content)})


def test_admin_endpoints_need_system_administrator(client):
    assert client.get("/api/v1/admin/companies").status_code == 401
    login(client)  # Company Administrator of ABC Corporation
    assert client.get("/api/v1/admin/companies").status_code == 403
    assert upload(client, "CMP-10045", b"x", "a.csv").status_code == 403
    login(client, "vera.viewer@abc.com", VIEWER_PASSWORD)
    assert client.get("/api/v1/admin/lookups").status_code == 403


def test_company_list_detail_and_users(client):
    sysadmin(client)
    companies = {c["id"]: c for c in client.get("/api/v1/admin/companies").json()}
    assert "SYS-PLATFORM" not in companies  # the platform company is never listed
    abc = companies["CMP-10045"]
    assert abc["name"] == "ABC Corporation" and abc["dealerCount"] == 57 and abc["isActive"] is True
    assert abc["userCount"] >= 2 and abc["address"]["country"] == "India"
    assert [c["id"] for c in client.get("/api/v1/admin/companies", params={"search": "other"}).json()] == ["CMP-20001"]
    assert client.get("/api/v1/admin/companies/SYS-PLATFORM").status_code == 404

    users = client.get("/api/v1/admin/companies/CMP-10045/users").json()
    john = next(u for u in users if u["email"] == "john.smith@abc.com")
    assert john["role"] == "Company Administrator" and john["isActive"] is True and "passwordHash" not in john

    lookups = client.get("/api/v1/admin/lookups").json()
    assert "India" in lookups["countries"] and lookups["dealerTypes"][0] == "Distributor" and "INR" in lookups["currencies"]


def test_create_update_deactivate_company(client):
    sysadmin(client)
    created = new_company(client, "Northwind Power", "admin@northwind.example", employees=120, founded=2004)
    code = created["id"]
    assert code.startswith("CMP-") and created["logoText"] == "NP" and created["userCount"] == 1
    assert created["sector"] == "Electrical & Electrical Equipment" and created["employees"] == 120

    duplicate = client.post(
        "/api/v1/admin/companies",
        json={"name": "Dup", "admin": {"name": "Dup Admin", "email": "ADMIN@northwind.example", "password": "Another-Pass-2026"}},
    )
    assert duplicate.status_code == 409
    bad_sector = client.post(
        "/api/v1/admin/companies",
        json={"name": "Bad", "sector": "Nope", "admin": {"name": "B A", "email": "b@bad.example", "password": "Bad-Pass-2026"}},
    )
    assert bad_sector.status_code == 422 and "sector" in bad_sector.json()["message"]
    weak = client.post(
        "/api/v1/admin/companies", json={"name": "Weak", "admin": {"name": "W A", "email": "w@weak.example", "password": "short"}}
    )
    assert weak.status_code == 422

    updated = client.put(
        f"/api/v1/admin/companies/{code}",
        json={"name": "Northwind Power Ltd", "logoText": "NW", "city": "Pune", "country": "india", "phone": "+91 20 5555 0101"},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["name"] == "Northwind Power Ltd" and body["address"]["city"] == "Pune" and body["address"]["country"] == "India"
    assert body["sector"] is None  # PUT replaces the whole profile

    # The new company's administrator can sign in until the company is deactivated.
    login(client, "admin@northwind.example", NEW_ADMIN_PASSWORD)
    assert client.get("/api/v1/companies/me").json()["name"] == "Northwind Power Ltd"
    sysadmin(client)
    assert client.delete(f"/api/v1/admin/companies/{code}").json()["isActive"] is False
    assert client.get("/api/v1/admin/companies", params={"includeInactive": "false", "search": "Northwind"}).json() == []
    response = client.post("/api/v1/auth/login", json={"email": "admin@northwind.example", "password": NEW_ADMIN_PASSWORD})
    assert response.status_code == 401
    sysadmin(client)
    assert client.post(f"/api/v1/admin/companies/{code}/activate").json()["isActive"] is True
    login(client, "admin@northwind.example", NEW_ADMIN_PASSWORD)


def test_dealer_upload_xlsx_insert_update_and_errors(client):
    sysadmin(client)
    code = new_company(client, "Upload Target Co", "admin@uploadtarget.example")["id"]
    rows = [
        ["Dealer ID", "Dealer Name", "Company Name", "Dealer Type", "Status", "Country", "Region", "Sector", "Products",
         "Email", "Phone", "Last Transaction Date", "Last Transaction Amount", "Currency", "Notes"],
        ["UT-1", "Alpha Electric", "Alpha Electric Pvt Ltd", "Distributor", "Active", "India", "North",
         "Electrical & Electrical Equipment", "MCB; Switchgear", "alpha@example.com", 9811122233, "2026-09-01",
         "1,250.50", "INR", "x"],
        ["", "Beta Traders", "", "reseller", "", "usa", "", "", "", "", "", "", "", "", ""],
        ["UT-3", "Gamma Ltd", "", "Partner", "Active", "Atlantis", "", "", "", "", "", "", "", "", ""],
        ["UT-4", "Delta", "", "", "Active", "India", "", "", "", "", "", "", "", "", ""],
        ["UT-1", "Alpha Again", "", "Distributor", "Active", "India", "", "", "", "", "", "", "", "", ""],
        ["UT-5", "Epsilon", "", "Distributor", "Active", "India", "", "", "", "not-an-email", "", "31/13/2026", "", "", ""],
    ]  # fmt: skip
    response = upload(client, code, xlsx(rows), "dealers.xlsx")
    assert response.status_code == 201, response.text
    result = response.json()
    assert (result["totalRows"], result["inserted"], result["updated"], result["failed"]) == (6, 2, 0, 4)
    assert result["fileFormat"] == "xlsx" and result["companyId"] == code and "uploadedBy" not in result
    assert result["ignoredColumns"] == ["Notes"] and result["columnMapping"]["dealer_name"] == "Dealer Name"
    messages = {issue["row"]: issue["message"] for issue in result["issues"]}
    assert "Unknown country 'Atlantis'" in messages[4]
    assert "missing: Dealer Type" in messages[5]
    assert "appears more than once" in messages[6]
    assert "Email" in messages[7]

    login(client, "admin@uploadtarget.example", NEW_ADMIN_PASSWORD)
    dealers = {d["dealer_id"]: d for d in client.get("/api/v1/dealers", params={"pageSize": 50}).json()["items"]}
    alpha = dealers["UT-1"]
    assert alpha["company_name"] == "Alpha Electric Pvt Ltd" and alpha["phone"] == "9811122233"
    assert alpha["product"] == ["MCB", "Switchgear"] and alpha["last_transaction_amount"] == "1250.5"
    assert alpha["currency"] == "INR" and alpha["last_transaction_date"] == "2026-09-01"
    beta = dealers["DLR-1001"]  # no Dealer ID -> next free code
    assert beta["dealer_name"] == "Beta Traders" and beta["dealer_type"] == "Reseller"
    assert beta["status"] == "Active" and beta["country"] == "United States" and beta["is_demo"] is False

    # Second upload: existing IDs are updated (only the columns in the file), new ones inserted.
    sysadmin(client)
    rows = [
        ["dealer_id", "status", "product", "region"],
        ["UT-1", "Inactive", "Cables", ""],
        ["ut-9", "Pending", "", ""],
    ]
    result = upload(client, code, xlsx(rows), "update.xlsx").json()
    assert (result["inserted"], result["updated"], result["failed"]) == (0, 1, 1)
    assert "missing: Dealer Name, Dealer Type, Country" in result["issues"][0]["message"]
    login(client, "admin@uploadtarget.example", NEW_ADMIN_PASSWORD)
    alpha = client.get("/api/v1/dealers/UT-1").json()
    assert alpha["status"] == "Inactive" and alpha["product"] == ["Cables"] and alpha["region"] == "Not Available"
    assert alpha["dealer_name"] == "Alpha Electric" and alpha["email"] == "alpha@example.com"

    # Saved only in dcp.dealers (+ product tables); the uploader is in created_by / modified_by.
    from sqlalchemy import inspect, select

    from app.core.database import get_engine, get_session_factory
    from app.models import Dealer, User

    assert "dealer_uploads" not in inspect(get_engine()).get_table_names(schema="dcp")
    with get_session_factory()() as db:
        sysadmin_id = db.scalar(select(User.id).where(User.email == SYSADMIN_EMAIL))
        dealer = db.scalar(select(Dealer).where(Dealer.dealer_code == "UT-1"))
        assert dealer.created_by == sysadmin_id and dealer.modified_by == sysadmin_id


def test_dealer_upload_csv_and_xls(client):
    sysadmin(client)
    code = new_company(client, "Format Test Co", "admin@formats.example")["id"]
    csv_text = "Dealer Name;Dealer Type;Country;City;Postal Code\nCafé Électrique;Service Center;France;Lyon;69002\n"
    result = upload(client, code, csv_text.encode("cp1252"), "dealers.csv").json()
    assert (result["fileFormat"], result["inserted"], result["failed"]) == ("csv", 1, 0)

    result = upload(client, code, (FIXTURES / "dealers_legacy.xls").read_bytes(), "legacy.xls").json()
    assert (result["fileFormat"], result["sheetName"], result["inserted"], result["failed"]) == ("xls", "Dealers", 2, 0)

    login(client, "admin@formats.example", NEW_ADMIN_PASSWORD)
    dealers = {d["dealer_name"]: d for d in client.get("/api/v1/dealers").json()["items"]}
    assert dealers["Café Électrique"]["postal_code"] == "69002" and dealers["Café Électrique"]["city"] == "Lyon"
    legacy = dealers["Legacy Electricals"]
    assert legacy["dealer_id"] == "XLS-1" and legacy["status"] == "Pending" and legacy["phone"] == "9876543210"
    assert legacy["verification_date"] == "2026-09-30" and legacy["product"] == ["Cables", "Transformers"]
    assert dealers["Old Format Traders"]["dealer_id"] == "DLR-1002"  # after DLR-1001 from the csv


def test_dealer_upload_json_like_dealers_json(client):
    """A .json list shaped like dealers.json uploads as it is (all fields, products, is_demo, created_at)."""
    sysadmin(client)
    code = new_company(client, "Json Co", "admin@json.example")["id"]
    content = (Path(__file__).resolve().parents[3] / "dealers.json").read_bytes()
    result = upload(client, code, content, "dealers.json").json()
    assert (result["fileFormat"], result["totalRows"], result["inserted"], result["failed"]) == ("json", 57, 57, 0)
    assert result["ignoredColumns"] == [] and len(result["columnMapping"]) == 25

    login(client, "admin@json.example", NEW_ADMIN_PASSWORD)
    kaveri = client.get("/api/v1/dealers/DLR-1001").json()
    seeded = json.loads(content)[0]
    for key in ("dealer_name", "company_name", "dealer_type", "status", "region", "city", "country", "sector", "product",
                "phone", "email", "verification_date", "is_demo"):  # fmt: skip
        assert kaveri[key] == seeded[key], key
    assert kaveri["created_at"].startswith("2025-02-01")
    ganesh = client.get("/api/v1/dealers/DLR-1002").json()
    assert ganesh["is_demo"] is True and ganesh["last_transaction_amount"] == "485000" and ganesh["currency"] == "INR"

    # Uploading the same file again updates the 57 dealers instead of duplicating them.
    sysadmin(client)
    again = upload(client, code, content, "dealers.json").json()
    assert (again["inserted"], again["updated"], again["failed"]) == (0, 57, 0)
    assert upload(client, code, b"{not json", "x.json").status_code == 422


def test_dealer_upload_rejections_and_template(client):
    sysadmin(client)
    assert upload(client, "CMP-20001", b"%PDF-1.4", "dealers.pdf").status_code == 415
    assert upload(client, "CMP-20001", b"foo,bar\n1,2\n", "x.csv").status_code == 422  # no dealer columns
    assert upload(client, "CMP-20001", b"not a workbook", "x.xlsx").status_code == 422
    assert upload(client, "CMP-99999", b"Dealer Name\nA\n", "x.csv").status_code == 404
    assert upload(client, "SYS-PLATFORM", b"Dealer Name\nA\n", "x.csv").status_code == 404

    code = new_company(client, "Dormant Co", "admin@dormant.example")["id"]
    client.delete(f"/api/v1/admin/companies/{code}")
    assert upload(client, code, b"Dealer Name\nA\n", "x.csv").status_code == 409

    template = client.get("/api/v1/admin/dealer-uploads/template")
    assert template.status_code == 200 and "dealer_upload_template.xlsx" in template.headers["content-disposition"]
    book = load_workbook(io.BytesIO(template.content))
    assert book.sheetnames == ["Dealers", "Allowed values", "How to use"]
    headers = [cell.value for cell in book["Dealers"][1]]
    assert headers[:3] == ["Dealer ID", "Dealer Name", "Company Name"]

    # The template's example row uploads cleanly.
    target = new_company(client, "Template Co", "admin@template.example")["id"]
    result = upload(client, target, template.content, "template.xlsx").json()
    assert (result["inserted"], result["failed"]) == (1, 0), result["issues"]


def test_company_admin_cannot_use_sysadmin_upload_on_own_company(client):
    login(client, "john.smith@abc.com", DEMO_PASSWORD)
    assert upload(client, "CMP-10045", b"Dealer Name\nA\n", "x.csv").status_code == 403
