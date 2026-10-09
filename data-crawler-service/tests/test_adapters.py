"""Adapters: open-data files (no AI), HTML tables (no AI) and the AI fallback with grounding."""

from __future__ import annotations

from crawler.adapters import ADAPTERS, Context, SourceConfig
from crawler.ai.extractor import DealerList, ExtractedDealer
from tests.conftest import FIXTURES, FakeExtractor, FakeWeb, fixture_text


def run(config: SourceConfig, settings, web: FakeWeb | None = None, extractor=None):
    ctx = Context(settings=settings, fetcher=(web or FakeWeb()).fetcher(settings), extractor=extractor)
    return list(ADAPTERS[config.adapter](config, ctx).run()), ctx


def test_mca_file_keeps_tobacco_companies_only(settings):
    config = SourceConfig(
        id="mca-up", adapter="tabular", kind="registry", profile="mca", name="MCA (UP)",
        source_url="https://www.data.gov.in/catalog/company-master-data", file=str(FIXTURES / "mca_sample.csv"),
    )  # fmt: skip
    candidates, ctx = run(config, settings)
    names = [c.dealer_name for c in candidates]
    assert "GANGA TEXTILES PRIVATE LIMITED" not in names  # NIC 13111 (textiles) is filtered out
    assert len(candidates) == 4 and ctx.stats["rows_read"] == 5

    bidi = candidates[0]
    assert (bidi.dealer_type, bidi.products) == ("Manufacturer", ["Bidi"])
    assert (bidi.state, bidi.postal_code) == ("Uttar Pradesh", "211008")
    assert bidi.cin == "U12002UP2005PTC030001" and bidi.source.external_id == bidi.cin
    assert bidi.website == "https://sharmabidi.example"  # company mail domain
    agra = candidates[1]
    assert agra.dealer_type == "Wholesaler" and agra.website is None  # gmail is not a website
    assert candidates[2].business_status == "Strike Off"
    naveen = candidates[3]  # NIC 51909 but the activity text says tobacco
    assert naveen.dealer_type == "Wholesaler" and naveen.products == ["Pan Masala", "Tobacco"]


def test_udyam_file(settings):
    config = SourceConfig(
        id="udyam-up", adapter="tabular", kind="msme_registry", profile="udyam", name="Udyam (UP)",
        file=str(FIXTURES / "udyam_sample.csv"),
    )  # fmt: skip
    candidates, _ = run(config, settings)
    assert [c.dealer_name for c in candidates] == ["Sharma Bidi Works", "Gupta Beedi Agency"]
    gupta = candidates[1]
    assert gupta.udyam_no == "UDYAM-UP-35-0067890" and gupta.city == "Lucknow" and gupta.dealer_type == "Wholesaler"
    assert gupta.products == ["Bidi", "Tobacco"]  # NIC 46307 only says tobacco; the name says beedi


def test_html_table_is_read_without_ai(settings):
    url = "https://board.example/exporters"
    web = FakeWeb({url: (200, fixture_text("board_list.html"), "text/html; charset=utf-8")})
    extractor = FakeExtractor()
    config = SourceConfig(
        id="board", adapter="html", kind="commodity_board", name="Board exporters", urls=[url], filter="none",
        default_dealer_type="Exporter / Importer", default_products=["Tobacco"],
    )  # fmt: skip
    candidates, ctx = run(config, settings, web, extractor)
    assert extractor.calls == 0 and ctx.stats["pages_read_by_tables"] == 1
    mysore, kolkata = candidates
    assert mysore.dealer_name == "Mysore Cigarette Exports Pvt Ltd" and mysore.gstin == "29AACCM5678B1ZC"
    assert (mysore.phone, mysore.email, mysore.postal_code, mysore.state) == (
        "+91 821 234 5678", "exports@mysorecig.example", "570016", "Karnataka",
    )  # fmt: skip
    assert mysore.dealer_type == "Exporter / Importer" and mysore.products == ["Cigarettes"]
    assert kolkata.products == ["Tobacco"] and kolkata.source.evidence["row"].startswith("2 | Kolkata")


def test_page_without_table_goes_to_ai_and_unverified_values_are_dropped(settings):
    url = "https://assoc.example/members"
    web = FakeWeb({url: (200, fixture_text("irregular_list.html"), "text/html")})
    answer = DealerList(
        is_business_list=True,
        dealers=[
            ExtractedDealer(dealer_name="Rao Tobacco Traders", business_type="Distributors", phones=["94401 23456"],
                            full_address="14 Main Road, Guntur, Andhra Pradesh 522001", products=["cigarettes", "bidi"]),
            ExtractedDealer(dealer_name="Lakshmi Zarda Company", phones=["99999 88888"],  # not on the page
                            emails=["info@lakshmi.example"], gstin="37AABCL1234A1Z5"),  # not on the page
            ExtractedDealer(dealer_name="Invented Agencies", phones=["90000 11111"]),  # business not on the page
        ],
    )  # fmt: skip
    extractor = FakeExtractor(dealers=answer)
    config = SourceConfig(id="assoc", adapter="html", kind="trade_fair", name="Association", urls=[url])
    candidates, ctx = run(config, settings, web, extractor)
    assert extractor.calls == 1 and ctx.stats["ai_records_rejected"] == 1
    rao, lakshmi = candidates
    assert rao.phone == "+91 94401 23456" and rao.dealer_type == "Distributor" and rao.postal_code == "522001"
    assert rao.products == ["Cigarettes", "Bidi"] and rao.state == "Andhra Pradesh"
    assert lakshmi.phone is None and lakshmi.email is None and lakshmi.gstin is None
    assert sorted(lakshmi.source.evidence["dropped_unverified"]) == ["email", "gstin", "phone"]
    assert lakshmi.products == ["Chewing Tobacco"]  # no products in the answer: taken from the name ("Zarda")
    assert "ignore previous instructions" not in str(extractor.asked)


def test_without_ai_the_page_is_skipped_not_guessed(settings):
    url = "https://assoc.example/members"
    web = FakeWeb({url: (200, fixture_text("irregular_list.html"), "text/html")})
    config = SourceConfig(id="assoc", adapter="html", kind="trade_fair", name="Association", urls=[url])
    candidates, ctx = run(config, settings, web, extractor=None)
    assert candidates == [] and ctx.stats["pages_skipped_no_ai"] == 1
