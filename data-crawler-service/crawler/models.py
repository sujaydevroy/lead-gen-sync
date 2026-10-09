"""Records flowing through the pipeline.

Candidate  one dealer as ONE source describes it (already normalised), plus where it came from.
Dealer     the merged view of all candidates that are the same business, ready to publish.

The published file uses the portal's dealer upload keys (dealers.json shape, see
backend/app/services/dealer_import_service.py FIELDS) plus a "sources" list for dcp.dealer_sources.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

# Source kinds, also stored in dcp.dealer_sources.source_kind (keep in sync with the column comment).
OFFICIAL_KINDS = {"registry", "msme_registry", "tax_registry", "food_licence", "commodity_board"}
SOURCE_KINDS = OFFICIAL_KINDS | {"trade_fair", "website", "open_data", "paid_api", "manual"}


class SourceRef(BaseModel):
    url: str
    kind: str
    name: str
    external_id: str | None = None
    evidence: dict[str, Any] | None = None
    first_seen: date | None = None
    last_seen: date | None = None

    @property
    def is_official(self) -> bool:
        return self.kind in OFFICIAL_KINDS


class Candidate(BaseModel):
    """One dealer from one source. Everything except dealer_name and source is optional."""

    dealer_name: str
    legal_name: str | None = None
    dealer_type: str | None = None
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None  # international format, e.g. "+91 98371 41116"
    website: str | None = None
    gstin: str | None = None
    cin: str | None = None
    udyam_no: str | None = None
    other_id: str | None = None  # licence / registration number with no standard format
    full_address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "India"
    products: list[str] = Field(default_factory=list)
    nic_code: str | None = None
    activity: str | None = None  # free-text business activity from the source
    business_status: str | None = None  # status at the source, e.g. MCA "Strike Off", GST "Cancelled"
    source: SourceRef
    extractor: str = "adapter"  # "adapter:<name>" or "ai:<model>"
    links_to: str | None = None  # Dealer ID this candidate was collected for (website enrichment)


class Dealer(BaseModel):
    """Merged dealer, ready for the upload file."""

    dealer_code: str
    dealer_name: str
    legal_name: str | None = None
    dealer_type: str
    status: str = "Pending"
    status_reason: str = ""
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    registration_no: str | None = None
    full_address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "India"
    region: str | None = None
    sector: str | None = None
    products: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    candidate_count: int = 0

    @property
    def primary_source(self) -> SourceRef | None:
        official = [s for s in self.sources if s.is_official]
        return (official or self.sources or [None])[0]

    def to_upload_row(self, verification_date: date) -> dict[str, Any]:
        """dealers.json-shaped row for the admin Dealer Upload (keys it maps to dcp.dealers columns)."""
        primary = self.primary_source
        return {
            "dealer_id": self.dealer_code,
            "dealer_name": self.dealer_name,
            "company_name": self.legal_name,
            "dealer_type": self.dealer_type,
            "status": self.status,
            "contact_person": self.contact_person,
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
            "registration_no": self.registration_no,
            "full_address": self.full_address,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "region": self.region,
            "sector": self.sector,
            "product": self.products,
            "source_url": primary.url if primary else None,
            "verification_date": verification_date.isoformat(),
            "is_demo": False,
            "sources": [
                {
                    "url": s.url,
                    "kind": s.kind,
                    "name": s.name,
                    "external_id": s.external_id,
                    "evidence": s.evidence,
                    "first_seen": s.first_seen.isoformat() if s.first_seen else None,
                    "last_seen": s.last_seen.isoformat() if s.last_seen else None,
                }
                for s in self.sources
            ],
        }
