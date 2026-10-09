"""AI extraction contract + grounding.

The AI only ever proposes values. `ground()` keeps a value only when it can be found in the page text the AI
was given (phones by their digits, everything else by normalised text), so a hallucinated phone, email or GSTIN
never reaches the output. Every kept record carries the page snippet it came from as evidence.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from crawler.ai.text import normalise_for_match


class ExtractedDealer(BaseModel):
    """One business as written on the page. Leave a field empty when the page doesn't state it."""

    dealer_name: str = Field(description="Business / firm name exactly as on the page")
    legal_name: str | None = Field(None, description="Registered legal name if different, e.g. '... Pvt Ltd'")
    business_type: str | None = Field(
        None, description="Role as worded on the page, e.g. distributor, wholesaler, exporter, manufacturer, retailer"
    )
    contact_person: str | None = None
    phones: list[str] = Field(default_factory=list, description="Phone numbers exactly as written")
    emails: list[str] = Field(default_factory=list)
    website: str | None = None
    gstin: str | None = Field(None, description="15-character GSTIN if shown")
    cin: str | None = Field(None, description="21-character company CIN if shown")
    other_id: str | None = Field(None, description="Any other registration / licence number shown for this business")
    full_address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    products: list[str] = Field(default_factory=list, description="Products / brands / categories the business deals in")


class DealerList(BaseModel):
    is_business_list: bool = Field(description="True when the page lists businesses (dealers, members, exporters ...)")
    dealers: list[ExtractedDealer] = Field(default_factory=list)


class BusinessProfile(BaseModel):
    """The business that owns a website (from its home / contact / about pages)."""

    is_business_site: bool = Field(description="True when these pages belong to one business")
    business: ExtractedDealer | None = None
    activity: str | None = Field(None, description="One sentence: what the business does, in the page's words")


class Extractor(Protocol):
    calls: int

    def extract_dealers(self, text: str, *, url: str, hint: str) -> DealerList: ...

    def extract_profile(self, text: str, *, url: str, expected_name: str | None) -> BusinessProfile: ...


class BudgetExhausted(Exception):
    """CRAWLER_LLM_MAX_CALLS reached: the rest of the run continues without AI."""


# -- grounding --------------------------------------------------------------------------------------------------


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def _phone_on_page(phone: str, page_digits_runs: list[str]) -> bool:
    digits = _digits(phone)
    if len(digits) < 8:
        return False
    tail = digits[-10:] if len(digits) >= 10 else digits
    return any(tail in run for run in page_digits_runs)


def _text_on_page(value: str, page_norm: str, *, fuzzy: bool = False) -> bool:
    needle = normalise_for_match(value)
    if not needle:
        return False
    if needle in page_norm:
        return True
    return fuzzy and len(needle) >= 12 and fuzz.partial_ratio(needle, page_norm) >= 92


def snippet(page_text: str, value: str, width: int = 160) -> str:
    index = page_text.lower().find(value.lower()[:40])
    if index < 0:
        return value[:width]
    start = max(0, index - width // 4)
    return " ".join(page_text[start : start + width].split())


def ground(dealer: ExtractedDealer, page_text: str) -> tuple[dict[str, Any], list[str]] | None:
    """Raw record (normalize.build_candidate keys) with only the values found on the page, plus dropped fields.

    None when even the business name is not on the page.
    """
    page_norm = normalise_for_match(page_text)
    # Digit runs with common phone separators removed ("+91 98371-41116" -> "919837141116")
    page_digit_runs = [_digits(m) for m in re.findall(r"\+?[\d][\d\s().-]{6,}\d", page_text)]
    if not _text_on_page(dealer.dealer_name, page_norm):
        return None

    raw: dict[str, Any] = {"dealer_name": dealer.dealer_name}
    dropped: list[str] = []
    checks = {
        "legal_name": False, "contact_person": False, "website": False, "other_id": False,
        "full_address": True, "city": False, "state": False, "postal_code": False,
    }  # field -> fuzzy match allowed  # fmt: skip
    for field, fuzzy in checks.items():
        value = getattr(dealer, field)
        if not value:
            continue
        if _text_on_page(value, page_norm, fuzzy=fuzzy):
            raw[field] = value
        else:
            dropped.append(field)
    for field in ("gstin", "cin"):
        value = getattr(dealer, field)
        if value:
            compact = re.sub(r"\s", "", value).upper()
            if compact in re.sub(r"\s", "", page_text).upper():
                raw[field] = compact
            else:
                dropped.append(field)
    phones = [p for p in dealer.phones if _phone_on_page(p, page_digit_runs)]
    emails = [e for e in dealer.emails if e.strip().lower() in page_text.lower()]
    dropped += ["phone"] * (len(dealer.phones) - len(phones)) + ["email"] * (len(dealer.emails) - len(emails))
    if phones:
        raw["phone"] = " / ".join(phones)
    if emails:
        raw["email"] = emails[0]
    products = [p for p in dealer.products if _text_on_page(p, page_norm)]
    if products:
        raw["products"] = products
    if dealer.business_type and _text_on_page(dealer.business_type, page_norm):
        raw["dealer_type"] = dealer.business_type
    return raw, dropped
