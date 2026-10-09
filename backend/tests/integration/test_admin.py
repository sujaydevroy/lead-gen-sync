"""System administrators: companies (CRUD + read-only users) and dealer file uploads."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from tests.conftest import DEMO_PASSWORD, OTHER_PASSWORD, SYSADMIN_EMAIL, SYSADMIN_PASSWORD, VIEWER_PASSWORD, login

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
# Lookup values the upload tests create (removed again after each test)
CREATED_COUNTRIES = ("Atlantis",)
CREATED_REGIONS = ("Bagmati", "Kanto")
CREATED_SECTORS = ("Test Crawl Sector",)
CREATED_TYPES = ("Test Agent",)
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


def upload(client, content: bytes, name: str):
    return client.post("/api/v1/admin/dealer-uploads", files={"file": (name, content)})


def find_dealer(client, name: str) -> dict:
    items = client.get("/api/v1/dealers", params={"search": name}).json()["items"]
    return next(d for d in items if d["dealer_name"] == name)


@pytest.fixture(autouse=True)
def remove_uploaded_dealers():
    """Dealers are one shared directory: drop the dealers a test uploaded so other tests still see the 57 seeded."""
    yield
    from sqlalchemy import delete, select

    from app.core.database import get_session_factory
    from app.models import Country, Dealer, DealerProduct, DealerSource, DealerType, Region, Sector

    seeded = {d["dealer_id"] for d in json.loads((Path(__file__).resolve().parents[3] / "dealers.json").read_bytes())}
    with get_session_factory()() as db:
        extra = select(Dealer.id).where(Dealer.dealer_code.not_in(seeded))
        db.execute(delete(DealerProduct).where(DealerProduct.dealer_id.in_(extra)))
        db.execute(delete(DealerSource).where(DealerSource.dealer_id.in_(extra)))
        db.execute(delete(Dealer).where(Dealer.dealer_code.not_in(seeded)))
        db.execute(delete(Region).where(Region.name.in_(CREATED_REGIONS)))
        atlantis = select(Country.id).where(Country.name.in_(CREATED_COUNTRIES))
        db.execute(delete(Region).where(Region.country_id.in_(atlantis)))
        db.execute(delete(Country).where(Country.name.in_(CREATED_COUNTRIES)))
        db.execute(delete(Sector).where(Sector.name.in_(CREATED_SECTORS)))
        db.execute(delete(DealerType).where(DealerType.name.in_(CREATED_TYPES)))
        db.commit()


def test_admin_endpoints_need_system_administrator(client):
    assert client.get("/api/v1/admin/companies").status_code == 401
    login(client)  # Company Administrator of ABC Corporation
    assert client.get("/api/v1/admin/companies").status_code == 403
    assert upload(client, b"x", "a.csv").status_code == 403
    login(client, "vera.viewer@abc.com", VIEWER_PASSWORD)
    assert client.get("/api/v1/admin/lookups").status_code == 403


def test_company_list_detail_and_users(client):
    sysadmin(client)
    companies = {c["id"]: c for c in client.get("/api/v1/admin/companies").json()}
    assert "SYS-PLATFORM" not in companies  # the platform company is never listed
    abc = companies["CMP-10045"]
    assert abc["name"] == "ABC Corporation" and "dealerCount" not in abc and abc["isActive"] is True
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
    new_company(client, "Upload Target Co", "admin@uploadtarget.example")
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
    response = upload(client, xlsx(rows), "dealers.xlsx")
    assert response.status_code == 201, response.text
    result = response.json()
    assert (result["totalRows"], result["inserted"], result["updated"], result["failed"]) == (6, 3, 0, 3)
    assert result["fileFormat"] == "xlsx" and "companyId" not in result and "uploadedBy" not in result
    assert result["ignoredColumns"] == ["Notes"] and result["columnMapping"]["dealer_name"] == "Dealer Name"
    assert result["createdLookups"] == {"Country": ["Atlantis"]}  # unknown values are created, not rejected
    messages = {issue["row"]: issue["message"] for issue in result["issues"]}
    assert 4 not in messages
    assert "missing: Dealer Type" in messages[5]
    assert "appears more than once" in messages[6]
    assert "Email" in messages[7]

    # Uploaded dealers belong to no company: any client sees them.
    login(client, "admin@uploadtarget.example", NEW_ADMIN_PASSWORD)
    alpha = client.get("/api/v1/dealers/UT-1").json()
    assert alpha["company_name"] == "Alpha Electric Pvt Ltd" and alpha["phone"] == "9811122233"
    assert alpha["product"] == ["MCB", "Switchgear"] and alpha["last_transaction_amount"] == "1250.5"
    assert alpha["currency"] == "INR" and alpha["last_transaction_date"] == "2026-09-01"
    beta = find_dealer(client, "Beta Traders")
    assert beta["dealer_id"] == "DLR-1058"  # no Dealer ID -> next free code after the seeded DLR-1001 ... DLR-1057
    assert beta["dealer_name"] == "Beta Traders" and beta["dealer_type"] == "Reseller"
    assert beta["status"] == "Active" and beta["country"] == "United States" and beta["is_demo"] is False

    # Second upload: existing IDs are updated (only the columns in the file), new ones inserted.
    sysadmin(client)
    rows = [
        ["dealer_id", "status", "product", "region"],
        ["UT-1", "Inactive", "Cables", ""],
        ["ut-9", "Pending", "", ""],
    ]
    result = upload(client, xlsx(rows), "update.xlsx").json()
    assert (result["inserted"], result["updated"], result["failed"]) == (0, 1, 1)
    assert "missing: Dealer Name, Dealer Type, Country" in result["issues"][0]["message"]
    login(client)  # ABC Corporation sees the same dealer
    alpha = client.get("/api/v1/dealers/UT-1").json()
    assert alpha["status"] == "Inactive" and alpha["product"] == ["Cables"] and alpha["region"] == "Not Available"
    assert alpha["dealer_name"] == "Alpha Electric" and alpha["email"] == "alpha@example.com"

    # Saved only in dcp.dealers (+ product tables); the uploader is in created_by / modified_by.
    from sqlalchemy import inspect, select

    from app.core.database import get_engine, get_session_factory
    from app.models import Dealer, User

    assert "dealer_uploads" not in inspect(get_engine()).get_table_names(schema="dcp")
    assert "company_id" not in {c["name"] for c in inspect(get_engine()).get_columns("dealers", schema="dcp")}
    with get_session_factory()() as db:
        sysadmin_id = db.scalar(select(User.id).where(User.email == SYSADMIN_EMAIL))
        dealer = db.scalar(select(Dealer).where(Dealer.dealer_code == "UT-1"))
        assert dealer.created_by == sysadmin_id and dealer.modified_by == sysadmin_id


def test_dealer_upload_csv_and_xls(client):
    sysadmin(client)
    csv_text = "Dealer Name;Dealer Type;Country;City;Postal Code\nCafé Électrique;Service Center;France;Lyon;69002\n"
    result = upload(client, csv_text.encode("cp1252"), "dealers.csv").json()
    assert (result["fileFormat"], result["inserted"], result["failed"]) == ("csv", 1, 0)

    result = upload(client, (FIXTURES / "dealers_legacy.xls").read_bytes(), "legacy.xls").json()
    assert (result["fileFormat"], result["sheetName"], result["inserted"], result["failed"]) == ("xls", "Dealers", 2, 0)

    login(client)
    cafe = find_dealer(client, "Café Électrique")
    assert cafe["postal_code"] == "69002" and cafe["city"] == "Lyon" and cafe["dealer_id"] == "DLR-1058"
    legacy = find_dealer(client, "Legacy Electricals")
    assert legacy["dealer_id"] == "XLS-1" and legacy["status"] == "Pending" and legacy["phone"] == "9876543210"
    assert legacy["verification_date"] == "2026-09-30" and legacy["product"] == ["Cables", "Transformers"]
    assert find_dealer(client, "Old Format Traders")["dealer_id"] == "DLR-1059"  # after DLR-1058 from the csv


def test_dealer_upload_json_like_dealers_json(client):
    """A .json list shaped like dealers.json uploads as it is (all fields, products, is_demo, created_at).

    The seed already holds these 57 Dealer IDs and Dealer ID is unique system-wide, so they are updated in place.
    """
    sysadmin(client)
    content = (Path(__file__).resolve().parents[3] / "dealers.json").read_bytes()
    result = upload(client, content, "dealers.json").json()
    outcome = (result["fileFormat"], result["totalRows"], result["inserted"], result["updated"], result["failed"])
    assert outcome == ("json", 57, 0, 57, 0)
    assert result["ignoredColumns"] == [] and len(result["columnMapping"]) == 25

    login(client)
    assert client.get("/api/v1/dealers").json()["totalDealers"] == 57  # no duplicates
    kaveri = client.get("/api/v1/dealers/DLR-1001").json()
    seeded = json.loads(content)[0]
    for key in ("dealer_name", "company_name", "dealer_type", "status", "region", "city", "country", "sector", "product",
                "phone", "email", "verification_date", "is_demo"):  # fmt: skip
        assert kaveri[key] == seeded[key], key
    assert kaveri["created_at"].startswith("2025-02-01")
    ganesh = client.get("/api/v1/dealers/DLR-1002").json()
    assert ganesh["is_demo"] is True and ganesh["last_transaction_amount"] == "485000" and ganesh["currency"] == "INR"

    sysadmin(client)
    assert upload(client, b"{not json", "x.json").status_code == 422


def test_dealer_upload_rejections_and_template(client):
    sysadmin(client)
    assert upload(client, b"%PDF-1.4", "dealers.pdf").status_code == 415
    assert upload(client, b"foo,bar\n1,2\n", "x.csv").status_code == 422  # no dealer columns
    assert upload(client, b"not a workbook", "x.xlsx").status_code == 422

    template = client.get("/api/v1/admin/dealer-uploads/template")
    assert template.status_code == 200 and "dealer_upload_template.xlsx" in template.headers["content-disposition"]
    book = load_workbook(io.BytesIO(template.content))
    assert book.sheetnames == ["Dealers", "Allowed values", "How to use"]
    headers = [cell.value for cell in book["Dealers"][1]]
    assert headers[:3] == ["Dealer ID", "Dealer Name", "Company Name"]

    # The template's example row uploads cleanly.
    result = upload(client, template.content, "template.xlsx").json()
    assert (result["inserted"], result["failed"]) == (1, 0), result["issues"]


def test_company_admin_cannot_use_sysadmin_upload_on_own_company(client):
    login(client, "john.smith@abc.com", DEMO_PASSWORD)
    assert upload(client, b"Dealer Name\nA\n", "x.csv").status_code == 403


def test_uploaded_dealers_join_the_shared_directory(client):
    """Dealers belong to no company: an upload adds to the one directory every client company sees."""
    sysadmin(client)
    before = client.get("/api/v1/admin/dealer-directory").json()["dealerCount"]
    rows = [
        ["Dealer ID", "Dealer Name", "Dealer Type", "Country", "Products"],
        ["DIR-1", "Directory Electricals", "Distributor", "India", "MCB; Cables"],
        ["", "Directory Traders", "Reseller", "Japan", ""],
    ]
    result = upload(client, xlsx(rows), "directory.xlsx").json()
    assert (result["inserted"], result["updated"], result["failed"]) == (2, 0, 0)
    assert client.get("/api/v1/admin/dealer-directory").json()["dealerCount"] == before + 2

    again = upload(client, xlsx(rows[:2]), "directory.xlsx").json()  # same Dealer ID -> update, not duplicate
    assert (again["inserted"], again["updated"]) == (0, 1)

    for email, password in (("john.smith@abc.com", DEMO_PASSWORD), ("omar@other.example", OTHER_PASSWORD)):
        login(client, email, password)
        assert client.get("/api/v1/dealers/DIR-1").json()["product"] == ["MCB", "Cables"]
        assert client.get("/api/v1/dealers").json()["totalDealers"] == before + 2


def test_sysadmin_edits_company_users(client):
    sysadmin(client)
    code = new_company(client, "Edit Users Co", "admin@editusers.example")["id"]
    user = client.get(f"/api/v1/admin/companies/{code}/users").json()[0]
    base = f"/api/v1/admin/companies/{code}/users/{user['id']}"

    edited = client.patch(base, json={"name": "Edna Editor", "jobTitle": "Head of Sales", "phone": "+91 98100 22222"})
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert (body["name"], body["jobTitle"], body["phone"], body["role"]) == (
        "Edna Editor",
        "Head of Sales",
        "+91 98100 22222",
        "Company Administrator",
    )
    assert client.patch(base, json={"jobTitle": ""}).json()["jobTitle"] is None  # cleared; other fields kept
    assert client.patch(base, json={"role": "Sales Manager"}).json()["role"] == "Sales Manager"
    assert client.patch(base, json={"role": "System Administrator"}).status_code == 422
    assert client.patch(base, json={"email": "john.smith@abc.com"}).status_code == 409
    assert client.patch(base, json={"email": "edna@editusers.example"}).json()["email"] == "edna@editusers.example"
    assert client.patch(f"/api/v1/admin/companies/CMP-10045/users/{user['id']}", json={"name": "Nope"}).status_code == 404

    assert client.post(f"{base}/unlock").json()["isLocked"] is False
    assert client.post(f"{base}/password", json={"password": "Edna-Temp-2026"}).status_code == 200
    login(client, "edna@editusers.example", "Edna-Temp-2026")
    assert client.patch(base, json={"name": "Self Edit"}).status_code == 403  # only system administrators
    assert "roles" in sysadmin(client).get("/api/v1/admin/lookups").json()


def test_company_has_one_user_mapping(client):
    """Demo 1:1 mapping: each company is shown with one user, its first user (no table changes)."""
    sysadmin(client)
    abc = next(c for c in client.get("/api/v1/admin/companies").json() if c["id"] == "CMP-10045")
    assert abc["user"]["email"] == "john.smith@abc.com" and abc["user"]["id"] == "USR-2001"  # first of several users
    created = new_company(client, "One User Co", "solo@oneuser.example")
    assert created["user"]["email"] == "solo@oneuser.example" and created["user"]["role"] == "Company Administrator"
    assert client.get(f"/api/v1/admin/companies/{created['id']}").json()["user"]["name"] == "One User Co Admin"
    found = client.get("/api/v1/admin/companies", params={"search": "solo@oneuser"}).json()  # search by the user too
    assert [c["id"] for c in found] == [created["id"]]


def test_dealer_upload_regions_per_country_and_new_lookups(client):
    """A region is looked up (or created) within the row's country; new countries / sectors / types are created."""
    sysadmin(client)
    rows = [
        ["Dealer ID", "Dealer Name", "Dealer Type", "Country", "Region", "Sector", "State"],
        ["RG-1", "Delhi Tobacco Traders", "Wholesaler", "India", "north", "Tobacco & Related Products", "Delhi"],
        ["RG-2", "Guwahati Distributors", "Distributor", "India", "North East", "", "Assam"],
        ["RG-3", "Kathmandu Leaf Co", "Exporter / Importer", "Nepal", "Bagmati", "", ""],
        ["RG-4", "Test Agency", "Test Agent", "India", "", "Test Crawl Sector", ""],
        ["RG-5", "Code Country", "Distributor", "ZZ", "", "", ""],
        ["RG-6", "Tokyo Imports", "Retailer", "Japan", "KANTO", "", ""],
    ]
    result = upload(client, xlsx(rows), "regions.xlsx").json()
    assert (result["inserted"], result["failed"]) == (5, 1), result["issues"]
    assert "Unknown country 'ZZ'" in result["issues"][0]["message"]
    assert result["createdLookups"] == {
        "Region": ["Bagmati", "Kanto"],
        "Dealer Type": ["Test Agent"],
        "Sector": ["Test Crawl Sector"],
    }

    from sqlalchemy import select

    from app.core.database import get_session_factory
    from app.models import Dealer

    with get_session_factory()() as db:
        dealers = {d.dealer_code: d for d in db.scalars(select(Dealer).where(Dealer.dealer_code.like("RG-%")))}
        assert dealers["RG-1"].region.name == "North" and dealers["RG-1"].region.country_id == dealers["RG-1"].country_id
        assert dealers["RG-2"].region.name == "North East"
        assert dealers["RG-3"].region.country_id == dealers["RG-3"].country_id
        assert dealers["RG-6"].region.name == "Kanto"

    # Moving a dealer to another country without a region clears the old country's region;
    # a region without a country uses the dealer's current country.
    rows = [["Dealer ID", "Country"], ["RG-1", "Japan"]]
    assert upload(client, xlsx(rows), "move.xlsx").json()["updated"] == 1
    rows = [["Dealer ID", "Region"], ["RG-2", "South"]]
    assert upload(client, xlsx(rows), "region.xlsx").json()["updated"] == 1
    login(client)
    assert client.get("/api/v1/dealers/RG-1").json()["region"] == "Not Available"
    assert client.get("/api/v1/dealers/RG-2").json()["region"] == "South"
    assert client.get("/api/v1/dealers/RG-1").json()["dealer_type"] == "Wholesaler"


def test_dealer_upload_keeps_every_source(client):
    """Source URL and a crawler "sources" list are kept in dcp.dealer_sources, one row per dealer + URL."""
    sysadmin(client)
    crawled = [
        {
            "dealer_name": "Sharma Tobacco Agencies",
            "dealer_type": "Distributor",
            "status": "Active",
            "country": "India",
            "region": "North",
            "registration_no": "09AAAPS1234A1Z5",
            "source_url": "https://data.gov.in/mca/up",
            "verification_date": "2026-10-01",
            "sources": [
                {"url": "https://data.gov.in/mca/up", "kind": "registry", "name": "MCA master data (UP)",
                 "external_id": "U16009UP2001PTC000001", "first_seen": "2026-09-01"},
                {"url": "https://gst.example/09AAAPS1234A1Z5", "kind": "tax_registry", "name": "GST verification",
                 "external_id": "09AAAPS1234A1Z5", "evidence": {"status": "Active", "nature": "Wholesale"}},
            ],
        }
    ]  # fmt: skip
    result = upload(client, json.dumps(crawled).encode(), "crawl.json").json()
    assert (result["inserted"], result["failed"], result["sourcesSaved"]) == (1, 0, 2), result["issues"]

    # Upload again later with a new source URL: rows are refreshed, not duplicated.
    crawled[0]["verification_date"] = "2026-11-15"
    crawled[0]["dealer_id"] = find_dealer(sysadmin(client), "Sharma Tobacco Agencies")["dealer_id"]
    crawled[0]["source_url"] = "https://tobaccoboard.example/dealers"
    result = upload(client, json.dumps(crawled).encode(), "crawl.json").json()
    assert (result["updated"], result["sourcesSaved"]) == (1, 3)

    from sqlalchemy import select

    from app.core.database import get_session_factory
    from app.models import Dealer, DealerSource

    with get_session_factory()() as db:
        rows = {
            s.source_url: s
            for s in db.scalars(select(DealerSource).join(Dealer).where(Dealer.dealer_name == "Sharma Tobacco Agencies"))
        }
    assert set(rows) == {"https://data.gov.in/mca/up", "https://gst.example/09AAAPS1234A1Z5",
                         "https://tobaccoboard.example/dealers"}  # fmt: skip
    mca = rows["https://data.gov.in/mca/up"]
    assert (mca.source_kind, mca.external_id, str(mca.first_seen_on), str(mca.last_seen_on)) == (
        "registry", "U16009UP2001PTC000001", "2026-09-01", "2026-11-15",
    )  # fmt: skip
    assert rows["https://gst.example/09AAAPS1234A1Z5"].evidence == {"status": "Active", "nature": "Wholesale"}
    assert rows["https://tobaccoboard.example/dealers"].source_kind == "upload"

    bad = [{**crawled[0], "dealer_id": "", "dealer_name": "Bad Sources", "sources": [{"kind": "registry"}]}]
    result = upload(client, json.dumps(bad).encode(), "bad.json").json()
    assert result["failed"] == 1 and "needs a url" in result["issues"][0]["message"]
