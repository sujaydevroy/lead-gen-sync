"""Sales uploads and server-side analytics / forecast.

An upload is stored as master + detail (see app/services/sales_upload_details.py):
    dcp.sales_uploads -> dcp.sales_upload_columns, dcp.sales_upload_rows, dcp.sales_records, dcp.sales_upload_issues
"""

from __future__ import annotations

import math
import re
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError, not_found
from app.core.security import now_utc
from app.models import (
    Company,
    Country,
    Currency,
    Dealer,
    Product,
    SalesRecord,
    SalesUpload,
    SalesUploadColumn,
    SalesUploadIssue,
    SalesUploadRow,
    User,
)
from app.schemas.common import Page
from app.schemas.sales import (
    FileMetadata,
    SalesUploadColumnOut,
    SalesUploadResult,
    SalesUploadRowOut,
    SalesUploadSummary,
    UploadedData,
    UploadIssue,
)
from app.services import exchange_rate_service
from app.services.analytics import sales_analytics as sa
from app.services.analytics import sales_forecast as sf
from app.services.analytics.jsmath import js_sum
from app.services.analytics.sales_parsing import ParsedSales, SalesFileError, parse_sales_rows, read_xlsx, read_xlsx_sheet
from app.services.sales_upload_details import column_definitions, has_details, insert_details, row_payloads, sha256_hex
from app.services.storage_service import build_key, get_storage

SAMPLE_DISPLAY_NAME = "sample_sales.xlsx (demo data)"
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_WARNINGS_RETURNED = 50
PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def _parse(content: bytes, file_name: str) -> tuple[str, ParsedSales]:
    settings = get_settings()
    if not file_name.lower().endswith(".xlsx"):
        raise ApiError(415, "Unsupported file type. Please upload an Excel .xlsx workbook.")
    if not content:
        raise ApiError(422, "The file is empty.")
    if len(content) > settings.max_upload_bytes:
        raise ApiError(413, f"The file is larger than {settings.max_upload_mb} MB.")
    try:
        sheet_name, raw_rows = read_xlsx_sheet(content, max_rows=settings.max_sales_rows)
        parsed = parse_sales_rows(raw_rows)
    except SalesFileError as exc:
        raise ApiError(422, str(exc)) from exc
    if not parsed.records:
        raise ApiError(422, "No valid sales rows were found in the first sheet.")
    return sheet_name, parsed


def _name_map(db: Session, stmt) -> dict[str, int]:
    return {name.lower(): id_ for id_, name in db.execute(stmt) if name}


def upload_sales_file(
    db: Session,
    company: Company,
    user: User,
    *,
    content: bytes,
    file_name: str,
    display_name: str | None = None,
    content_type: str | None = None,
) -> SalesUploadResult:
    """Store the workbook on disk and save master + detail rows in one transaction."""
    sheet_name, parsed = _parse(content, file_name)
    original_name = Path(file_name).name
    display_name = display_name or original_name

    storage = get_storage()
    storage_key = build_key(company.company_code, "sales", file_name=original_name)
    storage.save(storage_key, content)

    columns = column_definitions(parsed.headers, parsed.column_indexes)
    upload = SalesUpload(
        company_id=company.id,
        uploaded_by_user_id=user.id,
        file_name=display_name[:255],
        original_file_name=original_name[:255],
        sheet_name=sheet_name[:100],
        content_type=(content_type or XLSX_CONTENT_TYPE)[:150],
        file_size_bytes=len(content),
        file_sha256=sha256_hex(content),
        storage_backend=storage.backend,
        storage_path=storage_key,
        physical_path=storage.physical_path(storage_key)[:1000],
        status="ready",
        total_rows=len(parsed.rows),
        valid_rows=len(parsed.records),
        skipped_rows=len(parsed.rows) - len(parsed.records),
        column_mapping=parsed.columns,
        processed_on=now_utc(),
    )
    db.add(upload)
    db.flush()

    for warning in parsed.warnings:
        db.add(SalesUploadIssue(sales_upload_id=upload.id, row_number=warning["row"], message=warning["message"][:1000]))

    # Resolve names to reference rows where possible (raw text is always kept).
    dealers = _name_map(db, select(Dealer.id, Dealer.dealer_name).where(Dealer.company_id == company.id, Dealer.is_active))
    dealers |= {
        k: v
        for k, v in _name_map(
            db, select(Dealer.id, Dealer.legal_name).where(Dealer.company_id == company.id, Dealer.is_active)
        ).items()
        if k not in dealers
    }
    countries = _name_map(db, select(Country.id, Country.name))
    products = _name_map(db, select(Product.id, Product.name))
    currencies = _name_map(db, select(Currency.id, Currency.code))

    inserted = db.execute(
        insert(SalesRecord).returning(SalesRecord.id, SalesRecord.row_number),
        [
            {
                "company_id": company.id,
                "sales_upload_id": upload.id,
                "row_number": r["rowNumber"],
                "customer_name": r["customerName"][:250],
                "dealer_id": dealers.get(r["customerName"].lower()),
                "country_name": r["country"][:100],
                "country_id": countries.get(r["country"].lower()),
                "location": r["location"][:200] or None,
                "sales_year": r["year"],
                "sales_month": r["month"],
                "period_start": date(r["year"], r["month"], 1),
                "product_name": r["product"][:250],
                "product_id": products.get(r["product"].lower()),
                "unit_of_measure": r["unit"][:30] or None,
                "quantity": r["quantity"],
                "amount": r["amount"],
                "currency_code": r["currency"][:10],
                "currency_id": currencies.get(r["currency"].lower()),
                "created_by": user.id,
                "modified_by": user.id,
            }
            for r in parsed.records
        ],
    )
    record_ids = {row_number: record_id for record_id, row_number in inserted}
    insert_details(db, upload, columns, row_payloads(parsed, columns), record_ids, user.id)
    db.commit()

    return SalesUploadResult(
        upload_id=upload.id,
        uploaded_data=UploadedData(headers=parsed.headers, rows=parsed.rows),
        processed_data=parsed.records,
        file_metadata=_metadata(upload, parsed.warnings, parsed.columns),
    )


def upload_sample(db: Session, company: Company, user: User) -> SalesUploadResult:
    path = get_settings().sample_sales_file
    if not path.is_file():
        raise ApiError(404, "The sample sales file is not available on the server.")
    return upload_sales_file(db, company, user, content=path.read_bytes(), file_name=path.name, display_name=SAMPLE_DISPLAY_NAME)


def _metadata(upload: SalesUpload, warnings: list[dict], columns: dict[str, str]) -> FileMetadata:
    return FileMetadata(
        name=upload.file_name,
        size=upload.file_size_bytes,
        uploaded_at=upload.created_on or now_utc(),
        total_rows=upload.total_rows,
        valid_rows=upload.valid_rows,
        skipped_rows=upload.skipped_rows,
        warnings=[UploadIssue(row=w["row"], message=w["message"]) for w in warnings[:MAX_WARNINGS_RETURNED]],
        warning_count=len(warnings),
        columns=columns or {},
    )


# ---------------------------------------------------------------------------
# Read / list / delete
# ---------------------------------------------------------------------------


def _get_upload(db: Session, company: Company, upload_id: int) -> SalesUpload:
    upload = db.scalar(
        select(SalesUpload).where(SalesUpload.id == upload_id, SalesUpload.company_id == company.id, SalesUpload.is_active)
    )
    if upload is None:
        raise not_found(f"Sales upload {upload_id}")
    return upload


def latest_upload_id(db: Session, company: Company) -> int | None:
    return db.scalar(
        select(SalesUpload.id)
        .where(SalesUpload.company_id == company.id, SalesUpload.is_active, SalesUpload.status == "ready")
        .order_by(SalesUpload.created_on.desc(), SalesUpload.id.desc())
        .limit(1)
    )


def _record_to_dict(r: SalesRecord) -> dict[str, Any]:
    return {
        "id": f"S-{r.row_number}",
        "rowNumber": r.row_number,
        "customerName": r.customer_name,
        "country": r.country_name,
        "location": r.location or "",
        "year": r.sales_year,
        "month": r.sales_month,
        "period": f"{r.sales_year}-{r.sales_month:02d}",
        "product": r.product_name,
        "unit": r.unit_of_measure or "",
        "quantity": float(r.quantity) if r.quantity is not None else None,
        "amount": float(r.amount),
        "currency": r.currency_code,
    }


def load_records(db: Session, upload_id: int) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(SalesRecord)
        .where(SalesRecord.sales_upload_id == upload_id, SalesRecord.is_active)
        .order_by(SalesRecord.row_number)
    )
    return [_record_to_dict(r) for r in rows]


def _uploaded_data_from_detail(db: Session, upload_id: int) -> UploadedData:
    """Rebuild the sheet (headers + rows) from dcp.sales_upload_columns / dcp.sales_upload_rows."""
    columns = db.scalars(
        select(SalesUploadColumn)
        .where(SalesUploadColumn.sales_upload_id == upload_id, SalesUploadColumn.is_active)
        .order_by(SalesUploadColumn.column_index)
    ).all()
    rows = db.scalars(
        select(SalesUploadRow)
        .where(SalesUploadRow.sales_upload_id == upload_id, SalesUploadRow.is_active)
        .order_by(SalesUploadRow.row_number)
    )
    return UploadedData(
        headers=[c.header_name for c in columns],
        rows=[[row.row_data.get(c.data_key) for c in columns] for row in rows],
    )


def _uploaded_data_from_file_or_records(upload: SalesUpload, records: list[dict[str, Any]]) -> UploadedData:
    """Fallback for uploads made before the detail tables existed (until backfilled)."""
    storage = get_storage()
    if upload.storage_path and storage.exists(upload.storage_path):
        try:
            parsed = parse_sales_rows(read_xlsx(storage.read(upload.storage_path), max_rows=get_settings().max_sales_rows))
            return UploadedData(headers=parsed.headers, rows=parsed.rows)
        except SalesFileError:
            pass
    fields = ["customerName", "country", "location", "month", "year", "product", "unit", "quantity", "amount", "currency"]
    headers = [
        "CustomerName",
        "Country",
        "Location",
        "Month",
        "Year",
        "Product",
        "Unit Of Measurement",
        "Quantity",
        "Amount",
        "Currency",
    ]
    return UploadedData(headers=headers, rows=[[r[f] for f in fields] for r in records])


def get_upload(db: Session, company: Company, upload_id: int) -> SalesUploadResult:
    upload = _get_upload(db, company, upload_id)
    records = load_records(db, upload.id)
    if has_details(db, upload.id):
        uploaded = _uploaded_data_from_detail(db, upload.id)
    else:
        uploaded = _uploaded_data_from_file_or_records(upload, records)
    warnings = [{"row": i.row_number, "message": i.message} for i in upload.issues if i.is_active]
    return SalesUploadResult(
        upload_id=upload.id,
        uploaded_data=uploaded,
        processed_data=records,
        file_metadata=_metadata(upload, warnings, upload.column_mapping or {}),
    )


def _summary(upload: SalesUpload, uploaded_by: str) -> SalesUploadSummary:
    return SalesUploadSummary(
        upload_id=upload.id,
        file_name=upload.file_name,
        original_file_name=upload.original_file_name,
        sheet_name=upload.sheet_name,
        file_size=upload.file_size_bytes,
        file_sha256=upload.file_sha256,
        storage_path=upload.storage_path,
        status=upload.status,
        total_rows=upload.total_rows,
        valid_rows=upload.valid_rows,
        skipped_rows=upload.skipped_rows,
        column_count=upload.column_count,
        uploaded_by=uploaded_by,
        uploaded_at=upload.created_on,
    )


def list_uploads(db: Session, company: Company, limit: int = 50) -> list[SalesUploadSummary]:
    rows = db.execute(
        select(SalesUpload, User.full_name)
        .join(User, User.id == SalesUpload.uploaded_by_user_id)
        .where(SalesUpload.company_id == company.id, SalesUpload.is_active)
        .order_by(SalesUpload.created_on.desc(), SalesUpload.id.desc())
        .limit(limit)
    )
    return [_summary(upload, name) for upload, name in rows]


def list_columns(db: Session, company: Company, upload_id: int) -> list[SalesUploadColumnOut]:
    upload = _get_upload(db, company, upload_id)
    columns = db.scalars(
        select(SalesUploadColumn)
        .where(SalesUploadColumn.sales_upload_id == upload.id, SalesUploadColumn.is_active)
        .order_by(SalesUploadColumn.column_index)
    )
    return [
        SalesUploadColumnOut(
            column_index=c.column_index,
            column_letter=c.column_letter,
            header_name=c.header_name,
            data_key=c.data_key,
            mapped_field=c.mapped_field,
        )
        for c in columns
    ]


def list_rows(
    db: Session, company: Company, upload_id: int, *, valid: bool | None, page: int, page_size: int
) -> Page[SalesUploadRowOut]:
    upload = _get_upload(db, company, upload_id)
    conditions = [SalesUploadRow.sales_upload_id == upload.id, SalesUploadRow.is_active]
    if valid is not None:
        conditions.append(SalesUploadRow.is_valid.is_(valid))
    total = db.scalar(select(func.count(SalesUploadRow.id)).where(*conditions)) or 0
    total_pages = max(1, math.ceil(total / page_size))
    page = min(max(1, page), total_pages)
    rows = db.scalars(
        select(SalesUploadRow)
        .where(*conditions)
        .order_by(SalesUploadRow.row_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page[SalesUploadRowOut](
        items=[
            SalesUploadRowOut(row_number=r.row_number, is_valid=r.is_valid, sales_record_id=r.sales_record_id, data=r.row_data)
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_original_file(db: Session, company: Company, upload_id: int) -> tuple[SalesUpload, bytes]:
    """The workbook exactly as uploaded (from the storage backend)."""
    upload = _get_upload(db, company, upload_id)
    storage = get_storage()
    if not upload.storage_path or not storage.exists(upload.storage_path):
        raise not_found("The stored workbook")
    return upload, storage.read(upload.storage_path)


def delete_upload(db: Session, company: Company, upload_id: int) -> None:
    upload = _get_upload(db, company, upload_id)
    upload.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Analytics + forecast (port of frontend/src/hooks/useSalesAnalytics.js)
# ---------------------------------------------------------------------------


def normalise_filters(raw: dict[str, Any], rates: dict[str, float]) -> dict[str, Any]:
    filters = {**sa.default_filters(), **{k: v for k, v in raw.items() if v not in (None, "")}}
    for key in ("dateFrom", "dateTo"):
        if filters[key] and not PERIOD_RE.match(filters[key]):
            raise ApiError(422, f"{key} must be in YYYY-MM format.")
    filters["currency"] = str(filters["currency"]).upper()
    filters["reportingCurrency"] = str(filters["reportingCurrency"]).upper()
    if filters["currency"] == sa.ALL_CURRENCIES and filters["reportingCurrency"] not in rates:
        raise ApiError(422, f"No exchange rate for reporting currency {filters['reportingCurrency']}.")
    return filters


def json_safe(value: Any) -> Any:
    """Replace non-finite floats (e.g. infinite AICc) with None so the response is valid JSON."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def analytics(
    db: Session, company: Company, *, upload_id: int | None, raw_filters: dict[str, Any], scenario: str
) -> dict[str, Any]:
    upload_id = upload_id or latest_upload_id(db, company)
    fx = exchange_rate_service.effective_rates(db, company)
    if upload_id is None:
        return {"hasData": False, "uploadId": None, "fxRates": fx.rates, "fxAsOf": fx.as_of}
    upload = _get_upload(db, company, upload_id)
    records = load_records(db, upload.id)
    filters = normalise_filters(raw_filters, fx.rates)

    filtered = sa.apply_sales_filters(records, filters, fx.rates)
    rows = filtered["rows"]
    monthly = sa.aggregate_by_month(rows)
    products = sa.aggregate_by_product(rows)
    dealers = sa.aggregate_by_dealer(rows)
    regions = sa.aggregate_by_region(rows)
    forecast = (
        sf.generate_forecast(monthly)
        if monthly
        else {"status": "insufficient", "historyMonths": 0, "reason": "No sales match the selected filters."}
    )

    if forecast["status"] == "ok":
        values = sf.scenario_values(forecast, scenario)
        total = js_sum(p["value"] for p in values)
        chart_rows = sf.build_forecast_chart_rows(monthly, forecast, scenario)
        growth = sf.forecast_growth(monthly, total)
    else:
        total, growth = None, None
        chart_rows = sf.build_forecast_chart_rows(monthly, None)

    return json_safe(
        {
            "hasData": True,
            "uploadId": upload.id,
            "fileName": upload.file_name,
            "options": sa.get_sales_options(records),
            "filters": filters,
            "scenario": scenario,
            "currency": filtered["currency"],
            "converted": filtered["converted"],
            "excludedRows": filtered["excludedRows"],
            "unknownCurrencies": filtered["unknownCurrencies"],
            "skippedRows": upload.skipped_rows,
            "rowCount": len(rows),
            "monthly": monthly,
            "products": products,
            "dealers": dealers,
            "regions": regions,
            "kpis": sa.calculate_kpis(rows, monthly, products, dealers),
            "dealerConcentration": sa.concentration(dealers, 3),
            "productConcentration": sa.concentration(products, 3),
            "decliningDealers": sa.find_decliners(rows, monthly, "customerName"),
            "decliningProducts": sa.find_decliners(rows, monthly, "product"),
            "chartData": sa.build_sales_chart_data(rows),
            "forecast": forecast,
            "chartRows": chart_rows,
            "total": total,
            "growth": growth,
            "fxRates": fx.rates,
            "fxAsOf": fx.as_of.isoformat() if fx.as_of else None,
        }
    )


def forecast_only(
    db: Session, company: Company, *, upload_id: int | None, raw_filters: dict[str, Any], scenario: str
) -> dict[str, Any]:
    result = analytics(db, company, upload_id=upload_id, raw_filters=raw_filters, scenario=scenario)
    keys = ("hasData", "uploadId", "currency", "converted", "scenario", "monthly", "forecast", "chartRows", "total", "growth")
    return {k: result.get(k) for k in keys}
