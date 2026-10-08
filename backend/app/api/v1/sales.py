from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth, require_role
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.schemas.common import MessageResponse, Page
from app.schemas.sales import (
    ExchangeRatesOut,
    ExchangeRatesUpdate,
    SalesUploadColumnOut,
    SalesUploadResult,
    SalesUploadRowOut,
    SalesUploadSummary,
)
from app.services import exchange_rate_service, sales_service
from app.services.storage_service import safe_file_name

router = APIRouter(prefix="/sales", tags=["sales"])
ADMIN = "Company Administrator"
Scenario = Literal["conservative", "base", "optimistic"]


@router.post("/uploads", response_model=SalesUploadResult, status_code=201)
def upload(file: UploadFile = File(...), auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    """Upload an .xlsx workbook.

    Stores the file, then saves the master row (dcp.sales_uploads) and its detail: columns
    (dcp.sales_upload_columns), every row with all cells (dcp.sales_upload_rows) and the typed rows
    used by analytics (dcp.sales_records). Returns {uploadId, uploadedData, processedData, fileMetadata}.
    """
    limit = get_settings().max_upload_bytes
    content = file.file.read(limit + 1)
    if len(content) > limit:
        raise ApiError(413, f"The file is larger than {get_settings().max_upload_mb} MB.")
    return sales_service.upload_sales_file(
        db, auth.company, auth.user, content=content, file_name=file.filename or "upload.xlsx", content_type=file.content_type
    )


@router.post("/uploads/sample", response_model=SalesUploadResult, status_code=201)
def upload_sample(auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    """Load the bundled demo workbook (frontend/public/samples/sample_sales.xlsx)."""
    return sales_service.upload_sample(db, auth.company, auth.user)


@router.get("/uploads", response_model=list[SalesUploadSummary])
def list_uploads(auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return sales_service.list_uploads(db, auth.company)


@router.get("/uploads/{upload_id}", response_model=SalesUploadResult)
def get_upload(upload_id: int, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return sales_service.get_upload(db, auth.company, upload_id)


@router.get("/uploads/{upload_id}/columns", response_model=list[SalesUploadColumnOut])
def upload_columns(upload_id: int, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    """The sheet's columns in order: header, Excel letter, data key and recognised field."""
    return sales_service.list_columns(db, auth.company, upload_id)


@router.get("/uploads/{upload_id}/rows", response_model=Page[SalesUploadRowOut])
def upload_rows(
    upload_id: int,
    valid: bool | None = Query(None, description="true = rows used for analytics, false = rejected rows"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, alias="pageSize", ge=1, le=500),
    auth: AuthContext = Depends(get_auth),
    db: Session = Depends(get_db),
):
    """Every data row of the sheet with all of its cells (paginated)."""
    return sales_service.list_rows(db, auth.company, upload_id, valid=valid, page=page, page_size=page_size)


@router.get("/uploads/{upload_id}/file")
def download_original(upload_id: int, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    """Download the workbook exactly as it was uploaded."""
    upload, content = sales_service.get_original_file(db, auth.company, upload_id)
    name = upload.original_file_name or "sales.xlsx"
    return Response(
        content,
        media_type=upload.content_type or sales_service.XLSX_CONTENT_TYPE,
        headers={
            "Content-Disposition": f"attachment; filename=\"{safe_file_name(name)}\"; filename*=UTF-8''{quote(name)}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/uploads/{upload_id}", response_model=MessageResponse)
def delete_upload(upload_id: int, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    sales_service.delete_upload(db, auth.company, upload_id)
    return MessageResponse(message="Sales upload removed.")


@router.get("/exchange-rates", response_model=ExchangeRatesOut)
def get_rates(auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return exchange_rate_service.effective_rates(db, auth.company)


@router.put("/exchange-rates", response_model=ExchangeRatesOut)
def put_rates(payload: ExchangeRatesUpdate, auth: AuthContext = Depends(require_role(ADMIN)), db: Session = Depends(get_db)):
    """Company overrides of the indicative rates (USD per 1 unit). Administrators only."""
    return exchange_rate_service.update_rates(db, auth.company, payload.rates)


@router.delete("/exchange-rates", response_model=ExchangeRatesOut)
def reset_rates(auth: AuthContext = Depends(require_role(ADMIN)), db: Session = Depends(get_db)):
    """Remove company overrides ("Restore defaults")."""
    return exchange_rate_service.reset_overrides(db, auth.company)


def _filters(
    currency: str,
    reporting_currency: str,
    date_from: str,
    date_to: str,
    customers: list[str],
    products: list[str],
    countries: list[str],
) -> dict:
    return {
        "currency": currency,
        "reportingCurrency": reporting_currency,
        "dateFrom": date_from,
        "dateTo": date_to,
        "customers": customers,
        "products": products,
        "countries": countries,
    }


@router.get("/analytics")
def analytics(
    upload_id: int | None = Query(None, alias="uploadId"),
    currency: str = Query("ALL", max_length=10),
    reporting_currency: str = Query("USD", alias="reportingCurrency", max_length=3),
    date_from: str = Query("", alias="dateFrom", max_length=7),
    date_to: str = Query("", alias="dateTo", max_length=7),
    customers: list[str] = Query(default=[]),
    products: list[str] = Query(default=[]),
    countries: list[str] = Query(default=[]),
    scenario: Scenario = "base",
    auth: AuthContext = Depends(get_auth),
    db: Session = Depends(get_db),
):
    """KPIs, aggregations, decliners, concentration and the 12-month forecast (latest upload by default)."""
    filters = _filters(currency, reporting_currency, date_from, date_to, customers, products, countries)
    return sales_service.analytics(db, auth.company, upload_id=upload_id, raw_filters=filters, scenario=scenario)


@router.get("/forecast")
def forecast(
    upload_id: int | None = Query(None, alias="uploadId"),
    currency: str = Query("ALL", max_length=10),
    reporting_currency: str = Query("USD", alias="reportingCurrency", max_length=3),
    date_from: str = Query("", alias="dateFrom", max_length=7),
    date_to: str = Query("", alias="dateTo", max_length=7),
    customers: list[str] = Query(default=[]),
    products: list[str] = Query(default=[]),
    countries: list[str] = Query(default=[]),
    scenario: Scenario = "base",
    auth: AuthContext = Depends(get_auth),
    db: Session = Depends(get_db),
):
    """Forecast points (with 95% bounds), scenario totals, method and parameters."""
    filters = _filters(currency, reporting_currency, date_from, date_to, customers, products, countries)
    return sales_service.forecast_only(db, auth.company, upload_id=upload_id, raw_filters=filters, scenario=scenario)
