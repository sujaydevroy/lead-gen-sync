"""Uploaded workbooks are stored as master (dcp.sales_uploads) + detail (columns, rows, records)."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import delete, select

from app.core.database import get_session_factory
from app.models import SalesRecord, SalesUpload, SalesUploadColumn, SalesUploadRow, User
from app.services.sales_upload_details import backfill_upload
from app.services.storage_service import get_storage

SAMPLE = Path(__file__).resolve().parents[3] / "sample_sales.xlsx"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def workbook(rows, sheet="Q3 Sales"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def upload(client, content, name):
    response = client.post("/api/v1/sales/uploads", files={"file": (name, content, XLSX)})
    assert response.status_code == 201, response.text
    return response.json()["uploadId"]


def test_master_row_records_the_physical_file(auth_client):
    content = SAMPLE.read_bytes()
    upload_id = upload(auth_client, content, "sample_sales.xlsx")
    with get_session_factory()() as db:
        master = db.get(SalesUpload, upload_id)
        john = db.scalar(select(User).where(User.email == "john.smith@abc.com"))
        assert master.file_name == master.original_file_name == "sample_sales.xlsx"
        assert master.sheet_name == "Sheet1"
        assert master.content_type == XLSX
        assert master.file_size_bytes == len(content)
        assert master.file_sha256 == hashlib.sha256(content).hexdigest()
        assert master.storage_backend == "local"
        assert master.storage_path.startswith("CMP-10045/sales/") and master.storage_path.endswith("/sample_sales.xlsx")
        physical = Path(master.physical_path)
        assert physical.is_absolute() and physical.read_bytes() == content  # the file really is there
        assert (master.total_rows, master.valid_rows, master.skipped_rows, master.column_count) == (30, 30, 0, 10)
        assert master.created_by == john.id

        columns = db.scalars(
            select(SalesUploadColumn)
            .where(SalesUploadColumn.sales_upload_id == upload_id)
            .order_by(SalesUploadColumn.column_index)
        ).all()
        assert [c.header_name for c in columns][:3] == ["CustomerName", "Country", "Location"]
        assert [c.column_letter for c in columns] == list("ABCDEFGHIJ")
        assert {c.header_name: c.mapped_field for c in columns}["Unit Of Measurement"] == "unit"

        rows = db.scalars(
            select(SalesUploadRow).where(SalesUploadRow.sales_upload_id == upload_id).order_by(SalesUploadRow.row_number)
        ).all()
        assert len(rows) == 30 and all(r.is_valid for r in rows)
        first = rows[0]
        assert first.row_number == 2
        assert first.row_data == {
            "CustomerName": "Al Mansoori Trading LLC",
            "Country": "United Arab Emirates",
            "Location": "Dubai",
            "Month": "January",
            "Year": 2025,
            "Product": "Unmanufactured Tobacco (FCV Leaf)",
            "Unit Of Measurement": "MT",
            "Quantity": 120,
            "Amount": 468000,
            "Currency": "USD",
        }
        record = db.get(SalesRecord, first.sales_record_id)
        assert record.row_number == 2 and record.customer_name == "Al Mansoori Trading LLC"


def test_extra_columns_and_rejected_rows_are_kept(auth_client):
    content = workbook(
        [
            ["CustomerName", "Month", "Year", "Product", "Amount", "Currency", "Sales Rep", "", "Amount"],
            ["Acme", "March", 2025, "Cables", 1200, "INR", "Asha", "x", 5],
            ["", "April", 2025, "Cables", 100, "INR", "Ravi", None, None],  # no customer -> rejected
            ["Beta", 13, 2025, "Relays", 50, "USD", None, None, None],  # bad month -> rejected
        ]
    )
    upload_id = upload(auth_client, content, "q3 sales.xlsx")

    columns = auth_client.get(f"/api/v1/sales/uploads/{upload_id}/columns").json()
    assert [c["headerName"] for c in columns] == [
        "CustomerName",
        "Month",
        "Year",
        "Product",
        "Amount",
        "Currency",
        "Sales Rep",
        "Column H",
        "Amount",
    ]
    assert columns[6] == {
        "columnIndex": 7,
        "columnLetter": "G",
        "headerName": "Sales Rep",
        "dataKey": "Sales Rep",
        "mappedField": None,
    }
    assert columns[8]["dataKey"] == "Amount (I)" and columns[8]["mappedField"] is None  # duplicate header
    assert columns[4]["mappedField"] == "amount"

    rows = auth_client.get(f"/api/v1/sales/uploads/{upload_id}/rows").json()
    assert rows["total"] == 3
    assert rows["items"][0]["data"]["Sales Rep"] == "Asha" and rows["items"][0]["data"]["Amount (I)"] == 5
    assert rows["items"][0]["isValid"] and rows["items"][0]["salesRecordId"]
    rejected = auth_client.get(f"/api/v1/sales/uploads/{upload_id}/rows", params={"valid": "false"}).json()
    assert [r["rowNumber"] for r in rejected["items"]] == [3, 4]
    assert all(r["salesRecordId"] is None for r in rejected["items"])

    summary = next(u for u in auth_client.get("/api/v1/sales/uploads").json() if u["uploadId"] == upload_id)
    assert summary["originalFileName"] == "q3 sales.xlsx" and summary["sheetName"] == "Q3 Sales"
    assert summary["columnCount"] == 9 and summary["validRows"] == 1 and summary["skippedRows"] == 2


def test_download_original_and_reopen_without_the_file(auth_client):
    content = workbook([["CustomerName", "Month", "Year", "Product", "Amount", "Notes"], ["Acme", 1, 2026, "Fans", 10, "hi"]])
    upload_id = upload(auth_client, content, "réport.xlsx")

    download = auth_client.get(f"/api/v1/sales/uploads/{upload_id}/file")
    assert download.status_code == 200 and download.content == content
    assert "filename*=UTF-8''r%C3%A9port.xlsx" in download.headers["content-disposition"]

    # The sheet is rebuilt from the detail tables even if the stored file disappears.
    with get_session_factory()() as db:
        Path(db.get(SalesUpload, upload_id).physical_path).unlink()
    reopened = auth_client.get(f"/api/v1/sales/uploads/{upload_id}").json()
    assert reopened["uploadedData"] == {
        "headers": ["CustomerName", "Month", "Year", "Product", "Amount", "Notes"],
        "rows": [["Acme", 1, 2026, "Fans", 10, "hi"]],
    }
    assert auth_client.get(f"/api/v1/sales/uploads/{upload_id}/file").status_code == 404


def test_backfill_rebuilds_detail_for_older_uploads(auth_client):
    upload_id = upload(auth_client, SAMPLE.read_bytes(), "sample_sales.xlsx")
    no_file_id = upload(auth_client, SAMPLE.read_bytes(), "sample_sales.xlsx")
    # Make both look like uploads from before migration 0002.
    with get_session_factory()() as db:
        for uid in (upload_id, no_file_id):
            db.execute(delete(SalesUploadRow).where(SalesUploadRow.sales_upload_id == uid))
            db.execute(delete(SalesUploadColumn).where(SalesUploadColumn.sales_upload_id == uid))
            master = db.get(SalesUpload, uid)
            master.sheet_name = master.file_sha256 = master.physical_path = master.original_file_name = None
            master.column_count = 0
        Path(get_storage().physical_path(db.get(SalesUpload, no_file_id).storage_path)).unlink()
        db.commit()

        assert backfill_upload(db, db.get(SalesUpload, upload_id)) == "rebuilt from the stored workbook"
        assert backfill_upload(db, db.get(SalesUpload, no_file_id)) == "rebuilt from stored records (original workbook not found)"
        db.commit()
        assert backfill_upload(db, db.get(SalesUpload, upload_id)) == "already complete"

        rebuilt = db.get(SalesUpload, upload_id)
        assert rebuilt.sheet_name == "Sheet1" and rebuilt.column_count == 10 and Path(rebuilt.physical_path).is_file()
        assert rebuilt.original_file_name == "sample_sales.xlsx"
        rows = db.scalars(select(SalesUploadRow).where(SalesUploadRow.sales_upload_id == upload_id)).all()
        assert len(rows) == 30 and all(r.sales_record_id for r in rows)

        fallback_rows = db.scalars(
            select(SalesUploadRow).where(SalesUploadRow.sales_upload_id == no_file_id).order_by(SalesUploadRow.row_number)
        ).all()
        assert len(fallback_rows) == 30 and fallback_rows[0].row_data["CustomerName"] == "Al Mansoori Trading LLC"
        assert fallback_rows[0].row_data["Amount"] == 468000.0


def test_other_company_cannot_read_detail(client):
    from tests.conftest import DEMO_PASSWORD, OTHER_PASSWORD, login

    login(client)
    upload_id = upload(client, SAMPLE.read_bytes(), "sample_sales.xlsx")
    client.post("/api/v1/auth/logout")
    client.cookies.clear()
    login(client, "omar@other.example", OTHER_PASSWORD)
    for path in ("columns", "rows", "file"):
        assert client.get(f"/api/v1/sales/uploads/{upload_id}/{path}").status_code == 404
    assert DEMO_PASSWORD  # imported for symmetry with other tests
