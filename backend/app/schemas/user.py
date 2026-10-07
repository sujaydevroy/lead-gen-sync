from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import CamelModel


class UserOut(CamelModel):
    """Same shape as src/data/users.js."""

    id: str
    name: str
    email: str
    role: str
    job_title: str | None = None
    phone: str | None = None
    company_id: str
    country: str | None = None
    region: str | None = None


class SessionResponse(CamelModel):
    user: UserOut | None
    expires_at: datetime | None = None


class UserUpdate(CamelModel):
    name: str = Field(min_length=2, max_length=150)
    job_title: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, pattern=r"^[+()\d\s-]{7,20}$")

    @field_validator("name", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("job_title", "phone", mode="before")
    @classmethod
    def _strip_empty_to_none(cls, value):
        """Optional fields: trim, and treat an empty value as "not set" (before the phone pattern check)."""
        if isinstance(value, str):
            value = value.strip()
        return value or None


class UserSettingsOut(CamelModel):
    default_page_size: Literal[10, 20, 50] = 20
    apply_filters_instantly: bool = True
    desktop_dealer_view: Literal["table", "cards"] = "table"


class UserSettingsUpdate(UserSettingsOut):
    pass
