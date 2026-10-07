"""Detail storage for uploaded sales workbooks.

dcp.sales_uploads          master: file names, physical location, checksum, sheet, counts
dcp.sales_upload_columns   one row per sheet column (header, position, recognised field)
dcp.sales_upload_rows      one row per sheet data row, ALL cells as JSONB, linked to the typed
                           dcp.sales_records row when the row was valid
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import PurePosixPath
from typing import Any

from openpyxl.utils import get_column_letter
from sqlalchemy import exists, insert, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import SalesRecord, SalesUpload, SalesUploadColumn, SalesUploadRow
from app.services.analytics.sales_parsing import ParsedSales, SalesFileError, parse_sales_rows, read_xlsx_sheet
from app.services.storage_service import get_storage

logger = logging.getLogger("app.sales")

# Header text used when a column has to be rebuilt from typed records (original file unavailable).
FALLBACK_HEADERS = {
    "customerName": "CustomerName",
    "country": "Country",
    "location": "Location",
    "month": "Month",
    "year": "Year",
    "product": "Product",
    "unit": "Unit Of Measurement",
    "quantity": "Quantity",
    "amount": "Amount",
    "currency": "Currency",
}


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def column_definitions(headers: list[str], column_indexes: dict[str, int]) -> list[dict[str, Any]]:
    """Describe each sheet column. data_key is unique per upload and keys the row_data JSON."""
    mapped = {index: field for field, index in column_indexes.items()}
    used: set[str] = set()
    columns = []
    for i, header in enumerate(headers):
        letter = get_column_letter(i + 1)
        name = str(header).strip() if header not in (None, "") else ""
        display = (name or f"Column {letter}")[:255]
        key = display if display not in used else f"{display} ({letter})"[:255]
        used.add(key)
        columns.append(
            {
                "column_index": i + 1,
                "column_letter": letter,
                "header_name": display,
                "data_key": key,
                "mapped_field": mapped.get(i),
            }
        )
    return columns


def row_payloads(parsed: ParsedSales, columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One entry per data row: Excel row number, all cells keyed by data_key, valid flag."""
    valid_rows = {record["rowNumber"] for record in parsed.records}
    payloads = []
    for i, row in enumerate(parsed.rows):
        row_number = i + 2
        data = {
            col["data_key"]: (row[col["column_index"] - 1] if col["column_index"] - 1 < len(row) else None) for col in columns
        }
        payloads.append({"row_number": row_number, "row_data": data, "is_valid": row_number in valid_rows})
    return payloads


def insert_details(
    db: Session,
    upload: SalesUpload,
    columns: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    record_ids: dict[int, int],
    user_id: int | None,
) -> None:
    """Bulk-insert the column and row detail for an upload (audit columns set explicitly)."""
    audit = {"created_by": user_id, "modified_by": user_id}
    if columns:
        db.execute(insert(SalesUploadColumn), [{"sales_upload_id": upload.id, **col, **audit} for col in columns])
    if rows:
        db.execute(
            insert(SalesUploadRow),
            [
                {"sales_upload_id": upload.id, **row, "sales_record_id": record_ids.get(row["row_number"]), **audit}
                for row in rows
            ],
        )
    upload.column_count = len(columns)


def has_details(db: Session, upload_id: int) -> bool:
    return bool(db.scalar(select(exists().where(SalesUploadColumn.sales_upload_id == upload_id))))


def backfill_upload(db: Session, upload: SalesUpload) -> str:
    """Fill master file details + columns/rows for an upload made before migration 0002.

    Uses the stored workbook when it is still on disk; otherwise rebuilds the recognised columns
    and valid rows from dcp.sales_records (other columns and rejected rows can't be recovered).
    """
    if has_details(db, upload.id):
        return "already complete"
    record_ids = {
        row_number: record_id
        for record_id, row_number in db.execute(
            select(SalesRecord.id, SalesRecord.row_number).where(SalesRecord.sales_upload_id == upload.id)
        )
    }
    storage = get_storage()
    if not upload.original_file_name and upload.storage_path:
        upload.original_file_name = PurePosixPath(upload.storage_path).name[:255]

    if upload.storage_path and storage.exists(upload.storage_path):
        content = storage.read(upload.storage_path)
        try:
            sheet_name, raw_rows = read_xlsx_sheet(content, max_rows=get_settings().max_sales_rows)
            parsed = parse_sales_rows(raw_rows)
        except SalesFileError as exc:
            logger.warning("Backfill of upload %s could not re-read the workbook: %s", upload.id, exc)
        else:
            upload.sheet_name = sheet_name[:100]
            upload.file_sha256 = sha256_hex(content)
            upload.storage_backend = storage.backend
            upload.physical_path = storage.physical_path(upload.storage_path)[:1000]
            columns = column_definitions(parsed.headers, parsed.column_indexes)
            insert_details(db, upload, columns, row_payloads(parsed, columns), record_ids, upload.created_by)
            return "rebuilt from the stored workbook"

    # Original workbook unavailable: rebuild from the typed rows.
    # Typed records always carry these ten fields; use the original header text when it is known.
    mapping = upload.column_mapping or {}
    fields = list(FALLBACK_HEADERS)
    headers = [mapping.get(f) or FALLBACK_HEADERS[f] for f in fields]
    columns = column_definitions(headers, {f: i for i, f in enumerate(fields)})
    by_field = {col["mapped_field"]: col["data_key"] for col in columns}
    records = db.scalars(select(SalesRecord).where(SalesRecord.sales_upload_id == upload.id).order_by(SalesRecord.row_number))
    values = {
        "customerName": lambda r: r.customer_name,
        "country": lambda r: r.country_name,
        "location": lambda r: r.location,
        "month": lambda r: r.sales_month,
        "year": lambda r: r.sales_year,
        "product": lambda r: r.product_name,
        "unit": lambda r: r.unit_of_measure,
        "quantity": lambda r: float(r.quantity) if r.quantity is not None else None,
        "amount": lambda r: float(r.amount),
        "currency": lambda r: r.currency_code,
    }
    rows = [
        {
            "row_number": r.row_number,
            "row_data": {by_field[f]: values[f](r) for f in fields},
            "is_valid": True,
        }
        for r in records
    ]
    insert_details(db, upload, columns, rows, record_ids, upload.created_by)
    return "rebuilt from stored records (original workbook not found)"


def backfill_all(db: Session) -> list[tuple[int, str, str]]:
    """Backfill every upload that has no column/row detail yet. Returns (id, file name, outcome)."""
    uploads = db.scalars(
        select(SalesUpload).where(~exists().where(SalesUploadColumn.sales_upload_id == SalesUpload.id)).order_by(SalesUpload.id)
    ).all()
    results = []
    for upload in uploads:
        outcome = backfill_upload(db, upload)
        db.commit()
        results.append((upload.id, upload.file_name, outcome))
    return results
