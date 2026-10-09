"""System administration (companies, dealer uploads) and company user management payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import CamelModel
from app.schemas.company import CompanyOut

PHONE_PATTERN = r"^[+()\d\s-]{7,20}$"


def _blank_to_none(value):
    """Optional text fields: trim, and treat an empty value as "not set" (before pattern checks)."""
    if isinstance(value, str):
        value = value.strip()
    return value if value not in ("", None) else None


# --- Companies (system administrators) ---------------------------------------------------------


class CompanyFields(CamelModel):
    """Editable company profile. Sector / country / region are names from the lookups."""

    name: str = Field(min_length=2, max_length=200)
    logo_text: str | None = Field(default=None, max_length=10)
    industry: str | None = Field(default=None, max_length=150)
    sector: str | None = None
    website: str | None = Field(default=None, max_length=300)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    address_line1: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = None
    region: str | None = None
    registration_number: str | None = Field(default=None, max_length=100)
    tax_id: str | None = Field(default=None, max_length=100)
    employees: int | None = Field(default=None, ge=0)
    founded: int | None = Field(default=None, ge=1800, le=2200)

    @field_validator("name", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator(
        "logo_text", "industry", "sector", "website", "email", "phone", "address_line1", "city", "state",
        "postal_code", "country", "region", "registration_number", "tax_id", "employees", "founded",
        mode="before",
    )  # fmt: skip
    @classmethod
    def _optional(cls, value):
        return _blank_to_none(value)


class NewUserFields(CamelModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    job_title: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("name", "email", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("job_title", "phone", mode="before")
    @classmethod
    def _optional(cls, value):
        return _blank_to_none(value)


class CompanyCreate(CompanyFields):
    """A new company together with its first Company Administrator (who then manages its users)."""

    admin: NewUserFields


# --- Users -----------------------------------------------------------------------------------


class ManagedUserOut(CamelModel):
    id: str
    name: str
    email: str
    role: str
    job_title: str | None = None
    phone: str | None = None
    country: str | None = None
    region: str | None = None
    is_active: bool
    is_locked: bool
    last_login_on: datetime | None = None
    created_on: datetime


class AdminCompanyOut(CompanyOut):
    is_active: bool
    user_count: int
    created_on: datetime
    user: ManagedUserOut | None = None  # the company's one user (1:1 demo mapping: its first user)


class UserCreate(NewUserFields):
    role: str


class ManagedUserUpdate(CamelModel):
    """Company Administrators change a user's role and status (active / inactive)."""

    role: str | None = None
    is_active: bool | None = None


class AdminUserUpdate(CamelModel):
    """System administrators edit a company user's details and role (PATCH: only the fields sent change)."""

    name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    job_title: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    role: str | None = None

    @field_validator("name", "email", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("job_title", "phone", mode="before")
    @classmethod
    def _optional(cls, value):
        return _blank_to_none(value)


class PasswordSet(CamelModel):
    password: str = Field(min_length=1, max_length=200)


# --- Dealer uploads (system administrators) ----------------------------------------------------


class DealerDirectoryStats(CamelModel):
    dealer_count: int  # active dealers in dcp.dealers (one global directory, not owned by any company)


class DealerUploadIssue(CamelModel):
    row: int
    message: str


class DealerUploadOut(CamelModel):
    """Outcome of one upload (returned only; the rows themselves are saved in dcp.dealers)."""

    file_name: str
    file_format: str
    sheet_name: str | None = None
    total_rows: int
    inserted: int
    updated: int
    failed: int
    column_mapping: dict[str, str]
    issues: list[DealerUploadIssue]
    ignored_columns: list[str] = Field(default_factory=list)
    created_lookups: dict[str, list[str]] = Field(default_factory=dict)  # e.g. {"Country": ["Nepal"]}
    sources_saved: int = 0  # dcp.dealer_sources rows added or refreshed


class AdminLookups(CamelModel):
    roles: list[str]  # roles a company user can have
    countries: list[str]
    regions: list[str]  # distinct names over all countries
    regions_by_country: dict[str, list[str]]
    sectors: list[str]
    dealer_types: list[str]
    dealer_statuses: list[str]
    currencies: list[str]
