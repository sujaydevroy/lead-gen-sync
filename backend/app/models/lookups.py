from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base


class Role(AuditMixin, Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))


class Country(AuditMixin, Base):
    __tablename__ = "countries"
    name: Mapped[str] = mapped_column(String(100), unique=True)
    iso2_code: Mapped[str | None] = mapped_column(String(2))


class Region(AuditMixin, Base):
    __tablename__ = "regions"
    name: Mapped[str] = mapped_column(String(50), unique=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)


class Currency(AuditMixin, Base):
    __tablename__ = "currencies"
    code: Mapped[str] = mapped_column(String(3), unique=True)
    name: Mapped[str] = mapped_column(String(100))


class DealerType(AuditMixin, Base):
    __tablename__ = "dealer_types"
    name: Mapped[str] = mapped_column(String(50), unique=True)


class DealerStatus(AuditMixin, Base):
    __tablename__ = "dealer_statuses"
    name: Mapped[str] = mapped_column(String(50), unique=True)


class CommunicationType(AuditMixin, Base):
    __tablename__ = "communication_types"
    name: Mapped[str] = mapped_column(String(50), unique=True)


class CommunicationStatus(AuditMixin, Base):
    __tablename__ = "communication_statuses"
    name: Mapped[str] = mapped_column(String(50), unique=True)


class Sector(AuditMixin, Base):
    __tablename__ = "sectors"
    name: Mapped[str] = mapped_column(String(150), unique=True)
    sub_sectors: Mapped[list[SubSector]] = relationship(back_populates="sector", order_by="SubSector.sort_order")


class SubSector(AuditMixin, Base):
    __tablename__ = "sub_sectors"
    sector_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.sectors.id"))
    name: Mapped[str] = mapped_column(String(150))
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)
    sector: Mapped[Sector] = relationship(back_populates="sub_sectors")
