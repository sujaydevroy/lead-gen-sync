"""Dealer payloads use the same snake_case keys as dealers.json, which the UI already reads."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import CamelModel


class DealerOut(BaseModel):
    dealer_id: str
    dealer_name: str
    company_name: str
    dealer_type: str
    status: str
    contact_person: str
    region: str
    registration_no: str
    full_address: str
    city: str
    state: str
    postal_code: str
    email: str
    phone: str
    website: str
    country: str
    sector: str
    product: list[str]
    last_transaction_date: str
    last_transaction_amount: str
    currency: str
    source_url: str
    verification_date: str
    created_at: str
    is_demo: bool


class FacetOption(BaseModel):
    value: str
    count: int


class DealerFacets(CamelModel):
    regions_by_country: dict[str, list[str]]
    countries: list[FacetOption]
    regions: list[FacetOption]
    statuses: list[FacetOption]
    types: list[FacetOption]
    sectors: list[FacetOption]
    sub_sectors: list[FacetOption]


class DealerListResponse(CamelModel):
    items: list[DealerOut]
    total: int
    page: int
    page_size: int
    total_pages: int
    facets: DealerFacets
    total_dealers: int


class DealerFilters(CamelModel):
    countries: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    sub_sectors: list[str] = Field(default_factory=list)


class DealerStats(CamelModel):
    total_dealers: int
    active_dealers: int
    countries: int
    regions: int
