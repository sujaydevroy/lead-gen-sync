"""crawl -> enrich -> publish on the fixtures, and the output contract with the portal's Dealer Upload."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import yaml

from crawler.adapters import load_sources
from crawler.pipeline import build_dealers, crawl, enrich, make_context, publish
from crawler.resolve import IdentityMap, group
from tests.conftest import FIXTURES, FakeWeb, fixture_text

BOARD = "https://board.example/exporters"
SITE = "https://sharmabidi.example"


def write_sources(settings) -> None:
    settings.sources_file.write_text(
        yaml.safe_dump(
            {
                "sources": [
                    {"id": "mca-up", "adapter": "tabular", "kind": "registry", "profile": "mca", "name": "MCA (UP)",
                     "source_url": "https://www.data.gov.in/catalog/company-master-data",
                     "file": str(FIXTURES / "mca_sample.csv")},
                    {"id": "udyam-up", "adapter": "tabular", "kind": "msme_registry", "profile": "udyam",
                     "name": "Udyam (UP)", "source_url": "https://www.data.gov.in/catalog/udyam",
                     "file": str(FIXTURES / "udyam_sample.csv")},
                    {"id": "board", "adapter": "html", "kind": "commodity_board", "name": "Board exporters",
                     "urls": [BOARD], "filter": "none", "default_dealer_type": "Exporter / Importer"},
                ]
            }
        ),
        encoding="utf-8",
    )  # fmt: skip


def fake_web() -> FakeWeb:
    return FakeWeb(
        {
            BOARD: (200, fixture_text("board_list.html"), "text/html"),
            f"{SITE}": (200, fixture_text("site_home.html"), "text/html"),
            f"{SITE}/contact-us": (200, fixture_text("site_contact.html"), "text/html"),
        }
    )


def by_name(dealers):
    return {dealer.dealer_name: dealer for dealer, _ in dealers}


def test_crawl_enrich_publish(settings):
    write_sources(settings)
    web = fake_web()
    ctx = make_context(settings, use_ai=False, fetcher=web.fetcher(settings))
    found = crawl(ctx, load_sources(settings.sources_file))
    assert found == {"mca-up": 4, "udyam-up": 2, "board": 2}

    assert enrich(ctx, limit=10) == 1  # only Sharma Bidi has a website (company mail domain)
    dealers = by_name(build_dealers(settings))
    assert len(dealers) == 7

    sharma = dealers["Sharma Bidi Works"]  # MCA + Udyam (same name + PIN) + its website
    assert len(sharma.sources) == 3 and sharma.legal_name == "SHARMA BIDI WORKS PRIVATE LIMITED"
    assert (sharma.phone, sharma.email, sharma.contact_person) == ("+91 94150 12345", "orders@sharmabidi.example", None)
    assert sharma.registration_no == "U12002UP2005PTC030001" and sharma.region == "North"
    assert sharma.status == "Active" and sharma.dealer_type == "Manufacturer" and sharma.sector == "Tobacco & Related Products"

    assert dealers["ROYAL PAN MASALA PRIVATE LIMITED"].status == "Inactive"
    # Same accountant's e-mail on two companies: they stay two dealers.
    agra = dealers["AGRA TOBACCO DISTRIBUTORS PRIVATE LIMITED"]
    naveen = dealers["NAVEEN TRADING COMPANY PRIVATE LIMITED"]
    assert agra.dealer_code != naveen.dealer_code
    assert agra.status == "Pending" and "only one independent source" in agra.status_reason
    mysore = dealers["Mysore Cigarette Exports Pvt Ltd"]
    assert (mysore.region, mysore.registration_no, mysore.dealer_type) == ("South", "29AACCM5678B1ZC", "Exporter / Importer")

    report = publish(settings)
    assert report["dealers"] == 7 and report["by_status"] == {"Pending": 5, "Active": 1, "Inactive": 1}
    rows = json.loads(Path(report["files"][0]).read_text(encoding="utf-8"))
    sharma_row = next(r for r in rows if r["dealer_name"] == "Sharma Bidi Works")
    assert sharma_row["dealer_id"] == sharma.dealer_code and sharma_row["product"] == ["Bidi"]
    assert sharma_row["source_url"] == "https://www.data.gov.in/catalog/company-master-data"
    assert {s["kind"] for s in sharma_row["sources"]} == {"registry", "msme_registry", "website"}
    assert list(settings.output_dir.glob("report_*.md"))


def test_dealer_ids_are_stable_and_reuse_the_portals_ids(settings):
    write_sources(settings)
    ctx = make_context(settings, use_ai=False, fetcher=fake_web().fetcher(settings))
    crawl(ctx, load_sources(settings.sources_file))
    first = {d.dealer_name: d.dealer_code for d, _ in build_dealers(settings)}
    second = {d.dealer_name: d.dealer_code for d, _ in build_dealers(settings)}
    assert first == second and all(re.match(r"^CRW-[0-9A-F]{8}$", code) for code in first.values())

    # A dealer already in the portal (export with its registration number) keeps the portal's Dealer ID.
    settings.state_dir.joinpath("identity.json").unlink()
    existing = [{"dealer_id": "DLR-1500", "dealer_name": "Mysore Cigarette Exports", "registration_no": "29AACCM5678B1ZC"}]
    codes = {d.dealer_name: d.dealer_code for d, _ in build_dealers(settings, existing)}
    assert codes["Mysore Cigarette Exports Pvt Ltd"] == "DLR-1500"


def test_conflicting_registrations_are_never_merged(settings):
    from crawler.models import Candidate, SourceRef

    source = SourceRef(url="https://x.example", kind="registry", name="x")
    a = Candidate(dealer_name="Alpha Traders", cin="U46307UP2012PTC050002", phone="+91 98300 12345", source=source)
    b = Candidate(dealer_name="Alpha Traders", cin="U46307UP2012PTC050009", phone="+91 98300 12345", source=source)
    assert len(group([a, b])) == 2
    identities = IdentityMap(settings.state_dir / "identity.json")
    used: set[str] = set()
    first = identities.code_for(["cin:A"], ["email:shared@x.example"], used)
    used.add(first)
    identities.remember(["cin:A", "email:shared@x.example"], first)
    assert identities.code_for(["cin:B"], ["email:shared@x.example"], used) != first  # shared e-mail: new code


def test_upload_rows_use_only_columns_the_portal_accepts(settings):
    """Every key of a published row must be a header the backend's dealer upload recognises (FIELDS aliases)."""
    source = (FIXTURES.parents[2] / "backend" / "app" / "services" / "dealer_import_service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    fields = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "FIELDS"
    )
    accepted = {alias for _, aliases in fields.values() for alias in aliases}

    write_sources(settings)
    ctx = make_context(settings, use_ai=False, fetcher=fake_web().fetcher(settings))
    crawl(ctx, load_sources(settings.sources_file))
    rows = json.loads(Path(publish(settings)["files"][0]).read_text(encoding="utf-8"))
    for key in rows[0]:
        assert re.sub(r"[^a-z0-9]", "", key.lower()) in accepted, key
    allowed_types = {"Distributor", "Reseller", "Partner", "Service Center", "Wholesaler", "Retailer", "Manufacturer",
                     "Exporter / Importer"}  # fmt: skip
    assert {row["dealer_type"] for row in rows} <= allowed_types
    assert {row["region"] for row in rows} <= {"North", "South", "East", "West", "Central", "North East", None}
    assert all(row["status"] in {"Active", "Pending", "Inactive"} for row in rows)
