from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import CamelModel


class CompanyAddress(CamelModel):
    line1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    region: str | None = None


class CompanyOut(CamelModel):
    """Same shape as frontend/src/data/companies.js."""

    id: str
    name: str
    logo_text: str | None = None
    logo_url: str | None = None
    industry: str | None = None
    sector: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    address: CompanyAddress
    registration_number: str | None = None
    tax_id: str | None = None
    employees: int | None = None
    founded: str | None = None


class CompanyOptions(CamelModel):
    """Allowed values for the company profile form."""

    sectors: list[str]
    countries: list[str]
    regions: list[str]  # distinct names over all countries
    regions_by_country: dict[str, list[str]]


class SectorDefinition(BaseModel):
    """Same shape as an entry of sector.json."""

    sector: str
    sub_sectors: list[str]
