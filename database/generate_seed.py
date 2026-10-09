"""Generate database/03_seed.sql from the data the frontend already uses.

Sources (project root): sector.json, dealers.json. Company, user, currency and FX values
mirror frontend/src/data/companies.js, frontend/src/data/users.js and frontend/src/lib/fx.js.

Usage:
    python database/generate_seed.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "03_seed.sql"
NOT_AVAILABLE = "Not Available"
COMPANY_CODE = "CMP-10045"

ROLES = [
    ("Company Administrator", "Full access to company data, users and settings"),
    ("Sales Manager", "Manages dealers, communication and sales analytics"),
    ("Sales Representative", "Communicates with assigned dealers"),
    ("Viewer", "Read-only access"),
    ("System Administrator", "Platform owners: manage all companies and upload dealers"),
]
# Regions belong to a country. India: the zonal map used by the crawler (data-crawler-service/DESIGN.md).
# Other countries get the regions their dealers in dealers.json use, in this order.
INDIA_REGIONS = ["North", "South", "East", "West", "Central", "North East"]
REGION_ORDER = {name: i + 1 for i, name in enumerate(INDIA_REGIONS)}
# Mirrors frontend/src/lib/countries.js
COUNTRIES = {
    "India": "IN", "United States": "US", "Germany": "DE", "United Kingdom": "GB", "France": "FR",
    "Singapore": "SG", "Australia": "AU", "United Arab Emirates": "AE", "Japan": "JP", "Canada": "CA",
    "Belgium": "BE", "Egypt": "EG", "Indonesia": "ID", "Nepal": "NP", "Bangladesh": "BD", "Turkey": "TR",
    "Vietnam": "VN", "Philippines": "PH", "Russia": "RU", "Sri Lanka": "LK",
}
# Mirrors frontend/src/lib/fx.js (USD value of 1 unit; indicative reference values)
CURRENCIES = {
    "USD": ("US Dollar", 1), "EUR": ("Euro", 1.08), "GBP": ("Pound Sterling", 1.27),
    "INR": ("Indian Rupee", 0.012), "AED": ("UAE Dirham", 0.2723), "SGD": ("Singapore Dollar", 0.74),
    "AUD": ("Australian Dollar", 0.66), "CAD": ("Canadian Dollar", 0.73), "JPY": ("Japanese Yen", 0.0067),
}
FX_EFFECTIVE_DATE = "2026-10-01"
DEALER_TYPES = [
    "Distributor", "Reseller", "Partner", "Service Center",
    "Wholesaler", "Retailer", "Manufacturer", "Exporter / Importer",
]
DEALER_STATUSES = ["Active", "Inactive", "Pending"]
COMMUNICATION_TYPES = ["Email", "Message", "Call", "Meeting"]
COMMUNICATION_STATUSES = ["Sent", "Delivered", "Read", "Received", "Completed", "Initiated", "Scheduled", "Failed"]

# Mirrors frontend/src/lib/sectorMatching.js (product text -> Electrical & Electrical Equipment sub-sectors)
SUB_SECTOR_KEYWORDS = {
    "Electrical Switches": ["switch", "switches"],
    "Switchgear": ["switchgear", "ring main unit", "rmu", "breakers & switches"],
    "MCB & MCCB": ["mcb", "mccb", "breaker", "breakers", "circuit breaker"],
    "Distribution Boards": ["distribution board", "distribution boards"],
    "Electrical Panels": ["panel", "panels", "enclosure", "enclosures"],
    "Wires & Cables": ["wire", "wires", "cable", "cables"],
    "Industrial Cables": ["industrial cable", "industrial cables"],
    "House Wires": ["house wire", "house wires"],
    "Transformers": ["transformer", "transformers"],
    "Motors": ["motors", "electric motor"],
    "Generators": ["generator", "generators", "genset"],
    "Electrical Control Equipment": ["control products", "control equipment", "motor starter", "motor starters"],
    "Contactors": ["contactor", "contactors"],
    "Relays": ["relay", "relays"],
    "Capacitors": ["capacitor", "capacitors"],
    "Electrical Accessories": ["din rail", "accessories", "terminal block"],
    "Modular Switches": ["modular switch", "modular switches"],
    "Sockets & Plugs": ["socket", "sockets", "plug", "plugs"],
    "Fans": ["fan", "fans", "ceiling fan"],
    "Exhaust Fans": ["exhaust fan", "exhaust fans"],
    "LED Bulbs": ["led bulb", "led bulbs"],
    "LED Lights": ["led light", "led lights", "led panel"],
    "Commercial Lighting": ["commercial lighting"],
    "Industrial Lighting": ["industrial lighting", "high bay"],
    "Street Lighting": ["street lighting", "street light"],
    "Solar Lighting": ["solar lighting", "solar light"],
    "Batteries": ["battery", "batteries"],
    "Inverters": ["inverter", "inverters"],
    "UPS": ["ups"],
    "Stabilizers": ["stabilizer", "stabilizers", "stabiliser"],
    "Power Quality Equipment": ["power quality", "harmonic filter", "surge protection"],
    "Earthing Products": ["earthing", "grounding"],
    "Lightning Protection": ["lightning protection", "lightning"],
}


def product_matches(product: str, sub_sector: str) -> bool:
    terms = [sub_sector, *SUB_SECTOR_KEYWORDS.get(sub_sector, [])]
    pattern = r"(^|[^a-z0-9])(" + "|".join(re.escape(t.lower()) for t in terms) + r")($|[^a-z0-9])"
    return re.search(pattern, product.lower()) is not None


def lit(value) -> str:
    """SQL literal: NULL for missing / 'Not Available', otherwise a quoted string."""
    if value is None or value == "" or value == NOT_AVAILABLE:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return "'" + str(value).replace("'", "''") + "'"


def values_block(rows: list[tuple]) -> str:
    return ",\n".join("    (" + ", ".join(lit(v) for v in row) + ")" for row in rows)


def main() -> None:
    sectors = json.loads((ROOT / "sector.json").read_text(encoding="utf-8"))["sectors"]
    dealers = json.loads((ROOT / "dealers.json").read_text(encoding="utf-8"))
    company_sector = "Electrical & Electrical Equipment"
    company_sub_sectors = next(s["sub_sectors"] for s in sectors if s["sector"] == company_sector)

    products: dict[str, str] = {}
    for dealer in dealers:
        for p in dealer["product"]:
            products.setdefault(p.lower(), p)
    product_names = sorted(products.values(), key=str.lower)
    product_map = [(p, sub) for p in product_names for sub in company_sub_sectors if product_matches(p, sub)]

    out: list[str] = []
    w = out.append
    w("-- =============================================================================")
    w("-- Dealer Communication Portal - seed data")
    w("-- GENERATED by database/generate_seed.py from sector.json and dealers.json.")
    w("-- Do not edit by hand; re-run the generator instead.")
    w("-- Idempotent: every insert uses ON CONFLICT DO NOTHING.")
    w("--   psql \"$DATABASE_URL\" -v ON_ERROR_STOP=1 -f database/03_seed.sql")
    w("-- =============================================================================")
    w("")
    w("BEGIN;")
    w("SET search_path TO dcp, public;")
    w("")

    def simple(table: str, column: str, names: list[str]) -> None:
        w(f"INSERT INTO dcp.{table} ({column}) VALUES")
        w(values_block([(n,) for n in names]))
        w("ON CONFLICT DO NOTHING;")
        w("")

    w("-- Lookups ---------------------------------------------------------------------")
    w("INSERT INTO dcp.roles (name, description) VALUES")
    w(values_block(ROLES))
    w("ON CONFLICT DO NOTHING;")
    w("")
    w("INSERT INTO dcp.countries (name, iso2_code) VALUES")
    w(values_block(list(COUNTRIES.items())))
    w("ON CONFLICT DO NOTHING;")
    w("")
    region_rows = [("India", r) for r in INDIA_REGIONS]
    region_rows += sorted(
        {(d["country"], d["region"]) for d in dealers if d["region"] != NOT_AVAILABLE and d["country"] != "India"},
        key=lambda pair: (pair[0], REGION_ORDER.get(pair[1], 99), pair[1]),
    )
    w("INSERT INTO dcp.regions (country_id, name, sort_order)")
    w("SELECT c.id, v.name, v.sort_order::smallint")
    w("FROM (VALUES")
    w(",\n".join(f"    ({lit(c)}, {lit(r)}, {REGION_ORDER.get(r, 99)})" for c, r in region_rows))
    w(") AS v(country, name, sort_order)")
    w("JOIN dcp.countries c ON c.name = v.country")
    w("ON CONFLICT DO NOTHING;")
    w("")
    w("INSERT INTO dcp.currencies (code, name) VALUES")
    w(values_block([(code, name) for code, (name, _) in CURRENCIES.items()]))
    w("ON CONFLICT DO NOTHING;")
    w("")
    simple("dealer_types", "name", DEALER_TYPES)
    simple("dealer_statuses", "name", DEALER_STATUSES)
    simple("communication_types", "name", COMMUNICATION_TYPES)
    simple("communication_statuses", "name", COMMUNICATION_STATUSES)

    w(f"-- Sectors ({len(sectors)}) and sub-sectors (sector.json) -------------------------------")
    simple("sectors", "name", [s["sector"] for s in sectors])
    sub_rows = [(s["sector"], sub, i + 1) for s in sectors for i, sub in enumerate(s["sub_sectors"])]
    w("INSERT INTO dcp.sub_sectors (sector_id, name, sort_order)")
    w("SELECT s.id, v.name, v.sort_order::smallint")
    w("FROM (VALUES")
    w(",\n".join(f"    ({lit(a)}, {lit(b)}, {c})" for a, b, c in sub_rows))
    w(") AS v(sector, name, sort_order)")
    w("JOIN dcp.sectors s ON s.name = v.sector")
    w("ON CONFLICT DO NOTHING;")
    w("")

    w("-- Exchange rates (global defaults, USD per unit) -----------------------------")
    w("INSERT INTO dcp.exchange_rates (company_id, currency_id, rate_to_usd, effective_date, source)")
    w("SELECT NULL, c.id, v.rate::numeric, v.effective_date::date, v.source")
    w("FROM (VALUES")
    w(",\n".join(
        f"    ({lit(code)}, '{rate}', {lit(FX_EFFECTIVE_DATE)}, 'Indicative reference rate (demo default)')"
        for code, (_, rate) in CURRENCIES.items()
    ))
    w(") AS v(code, rate, effective_date, source)")
    w("JOIN dcp.currencies c ON c.code = v.code")
    w("ON CONFLICT DO NOTHING;")
    w("")

    w("-- Company (frontend/src/data/companies.js) --------------------------------------------")
    w("INSERT INTO dcp.companies (company_code, name, logo_text, industry, sector_id, website, email, phone,")
    w("    address_line1, city, state, postal_code, country_id, region_id, registration_number, tax_id,")
    w("    employee_count, founded_year)")
    w(f"SELECT {lit(COMPANY_CODE)}, 'ABC Corporation', 'ABC', 'Electrical Equipment Manufacturing', s.id,")
    w("    'https://www.abc-corp.example', 'contact@abc-corp.example', '+91 124 455 0190',")
    w("    'Tower B, 7th Floor, Cyber Park, Sector 39', 'Gurugram', 'Haryana', '122002', c.id, r.id,")
    w("    'U31900HR2009PLC045217', '06AABCA4521K1ZQ', 1250, 2009")
    w(f"FROM dcp.sectors s, dcp.countries c, dcp.regions r")
    w(f"WHERE s.name = {lit(company_sector)} AND c.name = 'India' AND r.country_id = c.id AND r.name = 'North'")
    w("ON CONFLICT DO NOTHING;")
    w("")

    w("-- User (frontend/src/data/users.js). password_hash stays NULL: set it with the backend CLI. --")
    w("INSERT INTO dcp.users (company_id, role_id, user_code, full_name, email, job_title, phone, country_id, region_id)")
    w("SELECT co.id, ro.id, 'USR-2001', 'John Smith', 'john.smith@abc.com', 'Head of Channel Sales', '+91 98110 45512', c.id, r.id")
    w("FROM dcp.companies co, dcp.roles ro, dcp.countries c, dcp.regions r")
    w(f"WHERE co.company_code = {lit(COMPANY_CODE)} AND ro.name = 'Company Administrator' AND c.name = 'India'")
    w("  AND r.country_id = c.id AND r.name = 'North'")
    w("ON CONFLICT DO NOTHING;")
    w("")
    w("INSERT INTO dcp.user_settings (user_id)")
    w("SELECT id FROM dcp.users WHERE user_code = 'USR-2001'")
    w("ON CONFLICT DO NOTHING;")
    w("")

    w(f"-- Products ({len(product_names)}) and their sub-sector mapping ({len(product_map)} links) ----------------")
    simple("products", "name", product_names)
    w("INSERT INTO dcp.product_sub_sectors (product_id, sub_sector_id)")
    w("SELECT p.id, ss.id")
    w("FROM (VALUES")
    w(values_block(product_map))
    w(") AS v(product, sub_sector)")
    w("JOIN dcp.products p ON lower(p.name) = lower(v.product)")
    w(f"JOIN dcp.sectors s ON s.name = {lit(company_sector)}")
    w("JOIN dcp.sub_sectors ss ON ss.sector_id = s.id AND ss.name = v.sub_sector")
    w("ON CONFLICT DO NOTHING;")
    w("")

    w(f"-- Dealers ({len(dealers)}) from dealers.json ------------------------------------------------")
    dealer_rows = [
        (
            d["dealer_id"], d["dealer_name"], d["company_name"], d["dealer_type"], d["status"], d["contact_person"],
            d["email"], d["phone"], d["website"], d["registration_no"], d["full_address"], d["city"], d["state"],
            d["postal_code"], d["country"], d["region"], d["sector"], d["last_transaction_date"],
            d["last_transaction_amount"], d["currency"], d["source_url"], d["verification_date"],
            "true" if d["is_demo"] else "false", d["created_at"],
        )
        for d in dealers
    ]
    w("INSERT INTO dcp.dealers (dealer_code, dealer_name, legal_name, dealer_type_id, dealer_status_id,")
    w("    contact_person, email, phone, website, registration_no, full_address, city, state, postal_code,")
    w("    country_id, region_id, sector_id, last_transaction_date, last_transaction_amount,")
    w("    last_transaction_currency_id, source_url, verification_date, is_demo, created_on)")
    w("SELECT v.dealer_code, v.dealer_name, v.legal_name, dt.id, ds.id,")
    w("    v.contact_person, v.email, v.phone, v.website, v.registration_no, v.full_address, v.city, v.state, v.postal_code,")
    w("    cn.id, rg.id, se.id, v.last_transaction_date::date, v.last_transaction_amount::numeric,")
    w("    cu.id, v.source_url, v.verification_date::date, v.is_demo::boolean, v.created_on::timestamptz")
    w("FROM (VALUES")
    w(values_block(dealer_rows))
    w(") AS v(dealer_code, dealer_name, legal_name, dealer_type, status, contact_person, email, phone, website,")
    w("       registration_no, full_address, city, state, postal_code, country, region, sector,")
    w("       last_transaction_date, last_transaction_amount, currency, source_url, verification_date, is_demo, created_on)")
    w("JOIN dcp.dealer_types dt ON dt.name = v.dealer_type")
    w("JOIN dcp.dealer_statuses ds ON ds.name = v.status")
    w("JOIN dcp.countries cn ON cn.name = v.country")
    w("LEFT JOIN dcp.regions rg ON rg.country_id = cn.id AND rg.name = v.region")
    w("LEFT JOIN dcp.sectors se ON se.name = v.sector")
    w("LEFT JOIN dcp.currencies cu ON cu.code = v.currency")
    w("ON CONFLICT DO NOTHING;")
    w("")

    dealer_products = [(d["dealer_id"], p, i + 1) for d in dealers for i, p in enumerate(d["product"])]
    w(f"-- Dealer products ({len(dealer_products)} links) -------------------------------------------")
    w("INSERT INTO dcp.dealer_products (dealer_id, product_id, sort_order)")
    w("SELECT d.id, p.id, v.sort_order::smallint")
    w("FROM (VALUES")
    w(",\n".join(f"    ({lit(a)}, {lit(b)}, {c})" for a, b, c in dealer_products))
    w(") AS v(dealer_code, product, sort_order)")
    w("JOIN dcp.dealers d ON d.dealer_code = v.dealer_code")
    w("JOIN dcp.products p ON lower(p.name) = lower(v.product)")
    w("ON CONFLICT DO NOTHING;")
    w("")
    w("-- Dealer sources: each dealer's source_url is its first source ------------------------")
    w("INSERT INTO dcp.dealer_sources (dealer_id, source_url, source_kind, first_seen_on, last_seen_on)")
    w("SELECT d.id, d.source_url, 'upload', COALESCE(d.verification_date, d.created_on::date),")
    w("    COALESCE(d.verification_date, d.created_on::date)")
    w("FROM dcp.dealers d")
    w("WHERE d.source_url IS NOT NULL")
    w("ON CONFLICT DO NOTHING;")
    w("")
    w("COMMIT;")
    w("")

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(sectors)} sectors, {len(sub_rows)} sub-sectors, "
          f"{len(product_names)} products, {len(product_map)} product/sub-sector links, "
          f"{len(dealers)} dealers, {len(dealer_products)} dealer/product links")


if __name__ == "__main__":
    main()
