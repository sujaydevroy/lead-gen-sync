from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base
from app.models.lookups import Currency


class SalesUpload(AuditMixin, Base):
    """Master row per uploaded workbook (details: columns, rows, records, issues)."""

    __tablename__ = "sales_uploads"
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.companies.id"))
    uploaded_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.users.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    original_file_name: Mapped[str | None] = mapped_column(String(255))
    sheet_name: Mapped[str | None] = mapped_column(String(100))
    content_type: Mapped[str | None] = mapped_column(String(150))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    storage_backend: Mapped[str] = mapped_column(String(20), default="local")
    storage_path: Mapped[str | None] = mapped_column(String(500))
    physical_path: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="processing")
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    column_mapping: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(String(1000))
    processed_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    issues: Mapped[list[SalesUploadIssue]] = relationship(lazy="selectin", order_by="SalesUploadIssue.row_number")


class SalesUploadIssue(AuditMixin, Base):
    __tablename__ = "sales_upload_issues"
    sales_upload_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.sales_uploads.id"))
    row_number: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(10), default="warning")
    message: Mapped[str] = mapped_column(String(1000))


class SalesUploadColumn(AuditMixin, Base):
    """One column of the uploaded sheet."""

    __tablename__ = "sales_upload_columns"
    sales_upload_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.sales_uploads.id"))
    column_index: Mapped[int] = mapped_column(SmallInteger)
    column_letter: Mapped[str] = mapped_column(String(3))
    header_name: Mapped[str] = mapped_column(String(255))
    data_key: Mapped[str] = mapped_column(String(255))
    mapped_field: Mapped[str | None] = mapped_column(String(50))


class SalesUploadRow(AuditMixin, Base):
    """One data row of the uploaded sheet with all of its cells."""

    __tablename__ = "sales_upload_rows"
    sales_upload_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.sales_uploads.id"))
    row_number: Mapped[int] = mapped_column(Integer)
    row_data: Mapped[dict] = mapped_column(JSONB)
    is_valid: Mapped[bool] = mapped_column(Boolean)
    sales_record_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.sales_records.id"))


class SalesRecord(AuditMixin, Base):
    __tablename__ = "sales_records"
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.companies.id"))
    sales_upload_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.sales_uploads.id"))
    row_number: Mapped[int] = mapped_column(Integer)
    customer_name: Mapped[str] = mapped_column(String(250))
    dealer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.dealers.id"))
    country_name: Mapped[str] = mapped_column(String(100))
    country_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.countries.id"))
    location: Mapped[str | None] = mapped_column(String(200))
    sales_year: Mapped[int] = mapped_column(SmallInteger)
    sales_month: Mapped[int] = mapped_column(SmallInteger)
    period_start: Mapped[date] = mapped_column(Date)
    product_name: Mapped[str] = mapped_column(String(250))
    product_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.products.id"))
    unit_of_measure: Mapped[str | None] = mapped_column(String(30))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency_code: Mapped[str] = mapped_column(String(10))
    currency_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.currencies.id"))


class ExchangeRate(AuditMixin, Base):
    __tablename__ = "exchange_rates"
    company_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dcp.companies.id"))
    currency_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dcp.currencies.id"))
    rate_to_usd: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    effective_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str | None] = mapped_column(String(200))
    currency: Mapped[Currency] = relationship(lazy="joined")
