"""Status per dealer (decision 5 in DESIGN.md).

Inactive  an official source says the business is closed (MCA struck off / dissolved / liquidated, GST cancelled).
Active    confirmed by at least two independent sources, at least one of them official, the PIN codes agree,
          and there is a phone or email to reach it.
Pending   everything else (with the reason, for the review queue).
"""

from __future__ import annotations

from crawler import india
from crawler.models import Candidate, Dealer

CLOSED_WORDS = ("strike off", "struck off", "striking off", "dissolved", "liquidat", "cancel", "amalgamated", "converted to llp",
                "not in operation", "closed")  # fmt: skip


def independent_sources(dealer: Dealer) -> set[str]:
    """Official registers count by kind (MCA, GST, Udyam are different registers even on one portal); other
    sources by the website that published them."""
    return {s.kind if s.is_official else (india.registrable_domain(s.url) or s.name) for s in dealer.sources}


def decide(dealer: Dealer, cluster: list[Candidate]) -> tuple[str, str]:
    for candidate in cluster:
        status = (candidate.business_status or "").lower()
        if candidate.source.is_official and any(word in status for word in CLOSED_WORDS):
            return "Inactive", f"{candidate.source.name}: {candidate.business_status}"

    missing: list[str] = []
    sources = independent_sources(dealer)
    if len(sources) < 2:
        missing.append("only one independent source")
    if not any(s.is_official for s in dealer.sources):
        missing.append("no official register")
    if not (dealer.phone or dealer.email):
        missing.append("no phone or email")
    pins = {c.postal_code for c in cluster if c.postal_code}
    if len(pins) > 1:
        missing.append(f"PIN codes disagree ({', '.join(sorted(pins))})")
    if missing:
        return "Pending", "; ".join(missing)
    return "Active", f"confirmed by {len(sources)} independent sources"
