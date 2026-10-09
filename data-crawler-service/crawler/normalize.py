"""Turn one raw record (any adapter or the AI extractor) into a normalised Candidate.

Raw keys: dealer_name, legal_name, dealer_type, contact_person, email, phone, website, gstin, cin, udyam_no,
other_id, full_address, city, state, postal_code, products, nic_code, activity, business_status.
Unknown or invalid values are dropped, never guessed: a wrong phone is worse than no phone.
"""

from __future__ import annotations

import re
from typing import Any

from crawler import classify, india
from crawler.models import Candidate, SourceRef

# Column limits of dcp.dealers (the upload rejects longer values)
MAX_LENGTHS = {
    "dealer_name": 200, "legal_name": 250, "contact_person": 150, "email": 254, "phone": 50, "website": 300,
    "other_id": 100, "full_address": 500, "city": 100, "state": 100, "postal_code": 20,
}  # fmt: skip


def _cut(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    limit = MAX_LENGTHS.get(field)
    return value[:limit].rstrip() if limit else value


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple):
        return [str(v) for v in value if v is not None]
    return [part for part in re.split(r"[;|\n]+", str(value)) if part.strip()]


def _nice_case(text: str | None) -> str | None:
    """'AGRA' -> 'Agra' for city names (dealer names keep the source's spelling)."""
    if text and text.isupper() and len(text) > 3:
        return text.title()
    return text


def build_candidate(
    raw: dict[str, Any], source: SourceRef, *, extractor: str = "adapter", default_type: str | None = None
) -> Candidate | None:
    name = india.dealer_name(raw.get("dealer_name")) or india.dealer_name(raw.get("legal_name"))
    if not name:
        return None
    legal = india.dealer_name(raw.get("legal_name"))

    other_id = india.clean_text(raw.get("other_id"))
    gst = india.gstin(raw.get("gstin")) or india.gstin(other_id)
    cin_info = india.cin(raw.get("cin")) or india.cin(other_id)
    udyam = india.udyam_no(raw.get("udyam_no")) or india.udyam_no(other_id)
    if other_id and other_id.replace(" ", "").upper() in {gst, cin_info.cin if cin_info else None, udyam}:
        other_id = None

    address = india.clean_text(raw.get("full_address"))
    postal = india.pin_code(raw.get("postal_code")) or india.pin_code(address)
    state_raw = india.clean_text(raw.get("state"))
    state = (
        india.state_name(state_raw, allow_codes=bool(state_raw and len(state_raw) <= 3))
        or india.state_in_text(address)
        or (cin_info.state if cin_info else None)
        or india.gstin_state(gst)
    )
    email = india.email(raw.get("email"))
    site = india.website(raw.get("website")) or india.website_from_email(email)

    nic = india.clean_text(raw.get("nic_code")) or (cin_info.nic_code if cin_info else None)
    activity = india.clean_text(raw.get("activity"))
    rule = classify.nic_rule(nic)
    product_text = " ; ".join([*_as_list(raw.get("products")), activity or ""])
    products = list(dict.fromkeys([*(rule[1] if rule else []), *classify.products_from_text(product_text)]))
    if set(products) <= {"Tobacco"}:  # nothing specific yet: the name may say it ("Gupta Beedi Agency")
        from_name = classify.products_from_text(f"{name} {legal or ''}")
        products = list(dict.fromkeys([*from_name, *products])) if from_name else products

    stated_type = india.clean_text(raw.get("dealer_type"))
    dealer_type = (
        (stated_type if stated_type in classify.DEALER_TYPES else classify.type_from_text(stated_type))
        or (rule[0] if rule else None)
        or classify.type_from_text(activity)
        or default_type
    )

    return Candidate(
        dealer_name=_cut(name, "dealer_name"),
        legal_name=_cut(legal if legal and legal != name else None, "legal_name"),
        dealer_type=dealer_type,
        contact_person=_cut(india.clean_text(raw.get("contact_person")), "contact_person"),
        email=_cut(email, "email"),
        phone=_cut(india.phone(raw.get("phone")), "phone"),
        website=_cut(site, "website"),
        gstin=gst,
        cin=cin_info.cin if cin_info else None,
        udyam_no=udyam,
        other_id=_cut(other_id, "other_id"),
        full_address=_cut(address, "full_address"),
        city=_cut(_nice_case(india.clean_text(raw.get("city"))), "city"),
        state=state,
        postal_code=postal,
        products=products,
        nic_code=nic,
        activity=activity,
        business_status=india.clean_text(raw.get("business_status")),
        source=source,
        extractor=extractor,
    )
