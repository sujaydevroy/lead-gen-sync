from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.common import CamelModel


class UploadedData(CamelModel):
    headers: list[str]
    rows: list[list[Any]]


class UploadIssue(CamelModel):
    row: int
    message: str


class FileMetadata(CamelModel):
    """Same shape as the Redux sales slice's fileMetadata."""

    name: str
    size: int
    uploaded_at: datetime
    total_rows: int
    valid_rows: int
    skipped_rows: int
    warnings: list[UploadIssue]
    warning_count: int
    columns: dict[str, str]


class SalesUploadResult(CamelModel):
    """{uploadedData, processedData, fileMetadata} — what the frontend stores in Redux."""

    upload_id: int
    uploaded_data: UploadedData
    processed_data: list[dict[str, Any]]
    file_metadata: FileMetadata


class SalesUploadSummary(CamelModel):
    """Master row (dcp.sales_uploads) as listed in "Recent uploads"."""

    upload_id: int
    file_name: str
    original_file_name: str | None = None
    sheet_name: str | None = None
    file_size: int
    file_sha256: str | None = None
    storage_path: str | None = None
    status: str
    total_rows: int
    valid_rows: int
    skipped_rows: int
    column_count: int = 0
    uploaded_by: str
    uploaded_at: datetime


class SalesUploadColumnOut(CamelModel):
    """Detail: one column of the uploaded sheet (dcp.sales_upload_columns)."""

    column_index: int
    column_letter: str
    header_name: str
    data_key: str
    mapped_field: str | None = None


class SalesUploadRowOut(CamelModel):
    """Detail: one data row of the uploaded sheet with all of its cells (dcp.sales_upload_rows)."""

    row_number: int
    is_valid: bool
    sales_record_id: int | None = None
    data: dict[str, Any]


class ExchangeRatesOut(CamelModel):
    as_of: date | None
    rates: dict[str, float]
    overridden: list[str]


class ExchangeRatesUpdate(CamelModel):
    rates: dict[str, float] = Field(min_length=1)

    @field_validator("rates")
    @classmethod
    def _positive(cls, value: dict[str, float]) -> dict[str, float]:
        cleaned = {}
        for code, rate in value.items():
            if rate is None or rate <= 0:
                raise ValueError(f"Rate for {code} must be greater than 0")
            cleaned[code.strip().upper()] = rate
        return cleaned
