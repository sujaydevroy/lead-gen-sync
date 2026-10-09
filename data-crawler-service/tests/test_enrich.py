"""Website enrichment: mailto / tel links first, AI only for what is still missing, wrong websites ignored."""

from __future__ import annotations

from crawler.adapters import Context
from crawler.ai.extractor import BusinessProfile, ExtractedDealer
from crawler.enrich import enrich_dealer
from crawler.models import Dealer
from tests.conftest import FakeExtractor, FakeWeb

SITE = "https://guptabeedi.example"
HOME = """<html><body><h1>Gupta Beedi Agency</h1><p>Wholesale distributors of beedi and cigarettes in Lucknow.</p>
<p>Call us on 0522 400 1234</p><a href="/about">About</a></body></html>"""


def dealer(**fields) -> Dealer:
    base = {"dealer_code": "CRW-1", "dealer_name": "Gupta Beedi Agency", "dealer_type": "Wholesaler", "website": SITE}
    return Dealer(**(base | fields))


def test_ai_fills_what_links_do_not_give_and_is_grounded(settings):
    web = FakeWeb({SITE: (200, HOME, "text/html"), f"{SITE}/about": (200, "<p>Founded 1990 by R. Gupta</p>", "text/html")})
    profile = BusinessProfile(
        is_business_site=True,
        business=ExtractedDealer(
            dealer_name="Gupta Beedi Agency",
            phones=["0522 400 1234"],
            emails=["sales@guptabeedi.example"],  # not on the page
            products=["beedi", "cigarettes"], business_type="Wholesale distributors",
        ),
        activity="Wholesale distributors of beedi and cigarettes",
    )  # fmt: skip
    extractor = FakeExtractor(profile=profile)
    ctx = Context(settings=settings, fetcher=web.fetcher(settings), extractor=extractor)
    candidate = enrich_dealer(dealer(), ctx)
    assert extractor.calls == 1 and candidate.links_to == "CRW-1"
    assert candidate.phone == "+91 522 400 1234" and candidate.email is None  # invented e-mail dropped
    assert candidate.products == ["Cigarettes", "Bidi"] and candidate.source.kind == "website"
    assert candidate.source.evidence["dropped_unverified"] == ["email"]
    assert candidate.source.evidence["pages"] == [SITE, f"{SITE}/about"]


def test_no_ai_call_when_links_already_give_everything(settings):
    page = '<a href="mailto:hello@guptabeedi.example">Mail</a> <a href="tel:+915224001234">Call</a>'
    web = FakeWeb({SITE: (200, page, "text/html")})
    extractor = FakeExtractor()
    ctx = Context(settings=settings, fetcher=web.fetcher(settings), extractor=extractor)
    candidate = enrich_dealer(dealer(products=["Bidi"]), ctx)
    assert extractor.calls == 0 and (candidate.email, candidate.phone) == ("hello@guptabeedi.example", "+91 522 400 1234")


def test_website_of_another_business_is_ignored(settings):
    web = FakeWeb({"https://sunrise.example": (200, "<h1>Sunrise Web Designers</h1><p>Call 0522 400 9999</p>", "text/html")})
    profile = BusinessProfile(
        is_business_site=True, business=ExtractedDealer(dealer_name="Sunrise Web Designers", phones=["0522 400 9999"])
    )
    ctx = Context(settings=settings, fetcher=web.fetcher(settings), extractor=FakeExtractor(profile=profile))
    assert enrich_dealer(dealer(website="https://sunrise.example"), ctx) is None
    assert ctx.stats["websites_other_business"] == 1
