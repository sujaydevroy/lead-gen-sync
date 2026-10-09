"""Dealer list behaviour must match the frontend's mock (frontend/src/lib/dealerFiltering.js) on the same data."""

from __future__ import annotations


def dealers(client, *pairs, **params):
    response = client.get("/api/v1/dealers", params=[*pairs, *params.items()])
    assert response.status_code == 200, response.text
    return response.json()


def test_default_list_shape_and_pagination(auth_client):
    body = dealers(auth_client)
    assert body["total"] == body["totalDealers"] == 57
    assert body["page"] == 1 and body["pageSize"] == 20 and body["totalPages"] == 3 and len(body["items"]) == 20
    # Sorted by name. Accented names follow the database collation, so only check the ASCII ones.
    names = [d["dealer_name"].lower() for d in body["items"] if d["dealer_name"].isascii()]
    assert names == sorted(names)
    last = dealers(auth_client, page=3)
    assert len(last["items"]) == 17
    assert dealers(auth_client, page=99)["page"] == 3  # clamped like the mock
    assert dealers(auth_client, pageSize=7)["pageSize"] == 20  # only 10 / 20 / 50 allowed


def test_filter_combinations_match_frontend(auth_client):
    india_north_active = dealers(auth_client, ("countries", "India"), ("regions", "North"), ("statuses", "Active"))
    assert india_north_active["total"] == 3
    assert {d["dealer_name"] for d in india_north_active["items"]} == {
        "CAPITAL ELECTRIC CORPORATION",
        "KAVERI ELECTRICALS",
        "Rajputana Switchgear House",
    }

    multi = dealers(
        auth_client,
        ("countries", "India"),
        ("countries", "Germany"),
        ("regions", "North"),
        ("regions", "South"),
        ("statuses", "Active"),
    )
    assert multi["total"] == 7

    sector = dealers(auth_client, ("sectors", "Electrical & Electrical Equipment"), ("subSectors", "Switchgear"))
    assert sector["total"] == 18


def test_facets_match_frontend(auth_client):
    facets = dealers(auth_client)["facets"]
    countries = {f["value"]: f["count"] for f in facets["countries"]}
    assert len(countries) == 10 and countries["India"] == 12 and countries["Japan"] == 5
    assert facets["sectors"] == [{"value": "Electrical & Electrical Equipment", "count": 45}]
    sub = {f["value"]: f["count"] for f in facets["subSectors"]}
    assert len(sub) == 33
    assert {
        k: sub[k]
        for k in (
            "Electrical Switches",
            "Switchgear",
            "MCB & MCCB",
            "Distribution Boards",
            "Electrical Panels",
            "Wires & Cables",
            "Industrial Cables",
            "House Wires",
        )
    } == {
        "Electrical Switches": 14,
        "Switchgear": 23,
        "MCB & MCCB": 19,
        "Distribution Boards": 5,
        "Electrical Panels": 20,
        "Wires & Cables": 17,
        "Industrial Cables": 10,
        "House Wires": 0,
    }
    assert [f["value"] for f in facets["statuses"]] == ["Active", "Inactive", "Pending"]
    assert facets["regionsByCountry"]["India"] == ["North", "South", "East", "West", "Central"]

    # Each facet ignores its own group: selecting India keeps other countries' counts visible.
    india = dealers(auth_client, ("countries", "India"))["facets"]
    assert {f["value"]: f["count"] for f in india["countries"]}["Germany"] == 5
    assert {f["value"]: f["count"] for f in india["regions"]}["North"] == 3


def test_search(auth_client):
    assert [d["dealer_name"] for d in dealers(auth_client, search="mumbai")["items"]] == ["Lamington Electric Mart"]
    assert dealers(auth_client, search="DLR-1001")["total"] == 1
    assert dealers(auth_client, search="%")["total"] == 0  # LIKE wildcards are escaped
    assert len(auth_client.get("/api/v1/dealers/search", params={"q": "electric", "limit": 3}).json()) == 3


def test_dealer_detail_uses_dealers_json_keys(auth_client):
    kaveri = auth_client.get("/api/v1/dealers/DLR-1001").json()
    assert kaveri["dealer_name"] == "KAVERI ELECTRICALS"
    assert kaveri["contact_person"] == "Not Available" and kaveri["website"] == "Not Available"
    assert kaveri["last_transaction_amount"] == "Not Available"
    assert kaveri["region"] == "North" and kaveri["city"] == "Agra" and kaveri["sector"] == "Tobacco & Related Products"
    assert kaveri["product"][:2] == ["Breakers & Switches", "Control Products"] and len(kaveri["product"]) == 9
    assert kaveri["is_demo"] is False

    ganesh = auth_client.get("/api/v1/dealers/dlr-1002").json()  # case-insensitive code
    assert ganesh["last_transaction_amount"] == "485000" and ganesh["currency"] == "INR"

    missing = auth_client.get("/api/v1/dealers/DLR-9999")
    assert missing.status_code == 404 and missing.json() == {"message": "Dealer DLR-9999 was not found."}


def test_recent_lookups_company_and_dashboard(auth_client):
    assert len(auth_client.get("/api/v1/dealers/recent", params={"limit": 5}).json()) == 5
    countries = auth_client.get("/api/v1/lookups/countries").json()
    assert {"name": "India", "count": 12} in countries
    regions = auth_client.get("/api/v1/lookups/regions", params={"country": "India"}).json()
    assert [r["name"] for r in regions] == ["North", "South", "East", "West", "Central"]
    assert auth_client.get("/api/v1/lookups/dealer-types").json() == [
        "Distributor", "Reseller", "Partner", "Service Center", "Wholesaler", "Retailer", "Manufacturer",
        "Exporter / Importer",
    ]  # fmt: skip

    company = auth_client.get("/api/v1/companies/me").json()
    assert company["id"] == "CMP-10045" and company["sector"] == "Electrical & Electrical Equipment"
    assert company["address"]["city"] == "Gurugram" and company["founded"] == "2009"
    sector = auth_client.get("/api/v1/companies/me/sector").json()
    assert sector["sector"] == "Electrical & Electrical Equipment" and len(sector["sub_sectors"]) == 33

    stats = auth_client.get("/api/v1/dashboard/stats").json()
    assert stats["dealers"] == {"totalDealers": 57, "activeDealers": 41, "countries": 10, "regions": 49}
