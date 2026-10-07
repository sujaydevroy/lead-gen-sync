from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base
from app.models.lookups import Country, Region, Role, Sector


class Company(AuditMixin, Base):
    __tablename__ = "companies"
    company_code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    logo_text: Mapped[str | None] = mapped_column(String(10))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str | None] = mapped_column(String(150))
    sector_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.sectors.id"))
    website: Mapped[str | None] = mapped_column(String(300))
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(50))
    address_line1: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.countries.id"))
    region_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.regions.id"))
    registration_number: Mapped[str | None] = mapped_column(String(100))
    tax_id: Mapped[str | None] = mapped_column(String(100))
    employee_count: Mapped[int | None] = mapped_column(Integer)
    founded_year: Mapped[int | None] = mapped_column(SmallInteger)

    sector: Mapped[Sector | None] = relationship(lazy="joined")
    country: Mapped[Country | None] = relationship(lazy="joined")
    region: Mapped[Region | None] = relationship(lazy="joined")


class User(AuditMixin, Base):
    __tablename__ = "users"
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.companies.id"))
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.roles.id"))
    user_code: Mapped[str] = mapped_column(String(30), unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    job_title: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(50))
    country_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.countries.id"))
    region_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.regions.id"))
    last_login_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped[Company] = relationship(lazy="joined")
    role: Mapped[Role] = relationship(lazy="joined")
    country: Mapped[Country | None] = relationship(lazy="joined")
    region: Mapped[Region | None] = relationship(lazy="joined")


class UserSettings(AuditMixin, Base):
    __tablename__ = "user_settings"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.users.id"), unique=True)
    default_page_size: Mapped[int] = mapped_column(SmallInteger, default=20)
    apply_filters_instantly: Mapped[bool] = mapped_column(Boolean, default=True)
    desktop_dealer_view: Mapped[str] = mapped_column(String(10), default="table")


class UserSession(AuditMixin, Base):
    __tablename__ = "user_sessions"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.users.id"))
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    remember_me: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(INET)


class PasswordResetToken(AuditMixin, Base):
    __tablename__ = "password_reset_tokens"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.users.id"))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
