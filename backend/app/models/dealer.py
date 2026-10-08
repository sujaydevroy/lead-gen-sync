from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base
from app.models.lookups import Country, Currency, DealerStatus, DealerType, Region, Sector, SubSector


class Product(AuditMixin, Base):
    __tablename__ = "products"
    name: Mapped[str] = mapped_column(String(200))


class ProductSubSector(AuditMixin, Base):
    __tablename__ = "product_sub_sectors"
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.products.id"))
    sub_sector_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.sub_sectors.id"))
    sub_sector: Mapped[SubSector] = relationship()


class Dealer(AuditMixin, Base):
    __tablename__ = "dealers"
    dealer_code: Mapped[str] = mapped_column(String(30))
    dealer_name: Mapped[str] = mapped_column(String(200))
    legal_name: Mapped[str | None] = mapped_column(String(250))
    dealer_type_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.dealer_types.id"))
    dealer_status_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.dealer_statuses.id"))
    contact_person: Mapped[str | None] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(50))
    website: Mapped[str | None] = mapped_column(String(300))
    registration_no: Mapped[str | None] = mapped_column(String(100))
    full_address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.countries.id"))
    region_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.regions.id"))
    sector_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.sectors.id"))
    last_transaction_date: Mapped[date | None] = mapped_column(Date)
    last_transaction_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    last_transaction_currency_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.currencies.id"))
    source_url: Mapped[str | None] = mapped_column(String(500))
    verification_date: Mapped[date | None] = mapped_column(Date)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    dealer_type: Mapped[DealerType] = relationship(lazy="joined")
    status: Mapped[DealerStatus] = relationship(lazy="joined")
    country: Mapped[Country] = relationship(lazy="joined")
    region: Mapped[Region | None] = relationship(lazy="joined")
    sector: Mapped[Sector | None] = relationship(lazy="joined")
    last_transaction_currency: Mapped[Currency | None] = relationship(lazy="joined")
    product_links: Mapped[list[DealerProduct]] = relationship(
        lazy="selectin",
        order_by="DealerProduct.sort_order",
        primaryjoin="and_(Dealer.id == DealerProduct.dealer_id, DealerProduct.is_active)",
        viewonly=True,
    )


class DealerProduct(AuditMixin, Base):
    __tablename__ = "dealer_products"
    dealer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.dealers.id"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.products.id"))
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)
    product: Mapped[Product] = relationship(lazy="joined")
