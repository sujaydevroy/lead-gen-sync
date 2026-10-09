"""Website enrichment: phone, email, contact person and products from a dealer's own website (hybrid).

For merged dealers that have a website (or a company mail domain) but miss a phone, an email or products:
1. HTTP first: read the home page and up to two contact / about pages of the same site, and take mailto: / tel:
   links (no AI).
2. AI only if something is still missing: the pages go to the extractor, the answer is grounded against the page
   text, and the business on the site must match the dealer's name (a wrong website is ignored).
The result is a "website" source candidate per dealer, saved as the `website` snapshot.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from rapidfuzz import fuzz

from crawler import india
from crawler.adapters.base import Context
from crawler.ai.extractor import BudgetExhausted, ground, snippet
from crawler.ai.text import html_to_text, links
from crawler.fetch import FetchError
from crawler.models import Candidate, Dealer, SourceRef
from crawler.normalize import build_candidate

CONTACT_LINK = re.compile(r"contact|about|reach|enquir|inquir|location|address|find-us|company", re.IGNORECASE)
MAX_EXTRA_PAGES = 2
NAME_MATCH_SCORE = 80


def needs_enrichment(dealer: Dealer) -> bool:
    return bool(dealer.website) and not (dealer.phone and dealer.email and dealer.products)


def _same_site(url: str, home: str) -> bool:
    return india.registrable_domain(url) == india.registrable_domain(home)


def _mailto_and_tel(html: str) -> tuple[list[str], list[str]]:
    emails = [m.split("?")[0] for m in re.findall(r'href=["\']mailto:([^"\']+)', html, re.IGNORECASE)]
    phones = re.findall(r'href=["\']tel:([^"\']+)', html, re.IGNORECASE)
    return emails, phones


def _name_matches(dealer: Dealer, site_name: str | None, home: str) -> bool:
    expected = india.name_key(dealer.dealer_name)
    if site_name and fuzz.token_set_ratio(expected, india.name_key(site_name)) >= NAME_MATCH_SCORE:
        return True
    domain = (india.registrable_domain(home) or "").split(".")[0]
    compact = expected.replace(" ", "")
    return bool(domain) and len(domain) >= 4 and (domain in compact or compact.startswith(domain[:6]))


def enrich_dealer(dealer: Dealer, ctx: Context) -> Candidate | None:
    home = dealer.website
    if not home:
        return None
    try:
        page = ctx.fetcher.get(home)
    except FetchError as exc:
        ctx.stats["websites_unreachable"] += 1
        ctx.log(f"  {dealer.dealer_code}: {exc}")
        return None
    pages = [(page.final_url, page.text())]
    for url, label in links(pages[0][1], page.final_url):
        if len(pages) > MAX_EXTRA_PAGES:
            break
        if _same_site(url, page.final_url) and (CONTACT_LINK.search(url) or CONTACT_LINK.search(label)):
            try:
                extra = ctx.fetcher.get(url)
            except FetchError:
                continue
            if all(extra.final_url != seen for seen, _ in pages):
                pages.append((extra.final_url, extra.text()))
    ctx.stats["websites_read"] += 1

    combined_text = "\n\n".join(f"[{url}]\n{html_to_text(html)}" for url, html in pages)
    emails: list[str] = []
    phones: list[str] = []
    for _, html in pages:
        found_emails, found_phones = _mailto_and_tel(html)
        emails += found_emails
        phones += found_phones
    raw: dict = {"dealer_name": dealer.dealer_name}
    if emails:
        raw["email"] = emails[0]
    if phones:
        raw["phone"] = " / ".join(dict.fromkeys(phones))
    extractor_label = "adapter:website_links"
    evidence: dict = {"pages": [url for url, _ in pages]}

    complete = (dealer.phone or raw.get("phone")) and (dealer.email or raw.get("email")) and dealer.products
    if not complete and ctx.extractor is not None:
        try:
            profile = ctx.extractor.extract_profile(combined_text, url=page.final_url, expected_name=dealer.dealer_name)
        except BudgetExhausted as exc:
            ctx.stats["websites_skipped_ai_budget"] += 1
            ctx.log(f"  {dealer.dealer_code}: {exc}")
            profile = None
        if profile and profile.is_business_site and profile.business:
            if not _name_matches(dealer, profile.business.dealer_name, page.final_url):
                ctx.stats["websites_other_business"] += 1
                ctx.log(f"  {dealer.dealer_code}: {page.final_url} looks like another business; ignored")
                return None
            grounded = ground(profile.business, combined_text)
            if grounded:
                ai_raw, dropped = grounded
                ai_raw["dealer_name"] = dealer.dealer_name
                ai_raw.update({k: v for k, v in raw.items() if v})  # mailto: / tel: links win
                raw = ai_raw
                if profile.activity:
                    raw["activity"] = profile.activity
                extractor_label = f"ai:{ctx.settings.llm_model}"
                evidence["snippet"] = snippet(combined_text, profile.business.dealer_name)
                if dropped:
                    evidence["dropped_unverified"] = dropped
    elif not raw.get("email") and not raw.get("phone"):
        ctx.stats["websites_without_contacts"] += 1

    raw.setdefault("website", page.final_url)
    source = SourceRef(
        url=page.final_url,
        kind="website",
        name=f"Website {urlsplit(page.final_url).netloc}",
        evidence=evidence,
        first_seen=ctx.today,
        last_seen=ctx.today,
    )
    candidate = build_candidate(raw, source, extractor=extractor_label)
    if candidate is None:
        return None
    candidate.links_to = dealer.dealer_code  # merged into that dealer at publish time
    ctx.stats["websites_enriched"] += 1
    return candidate
