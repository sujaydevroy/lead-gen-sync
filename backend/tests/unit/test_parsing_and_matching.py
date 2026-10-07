from __future__ import annotations

import io

import pytest
from openpyxl import Workbook

from app.core.rate_limit import RateLimiter
from app.services.analytics.sales_parsing import SalesFileError, parse_sales_rows, read_xlsx
from app.services.analytics.sector_matching import matching_sub_sectors, product_matches_sub_sector
from app.services.storage_service import LocalStorage, safe_file_name

HEADER = [
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


def workbook_bytes(rows):
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_parses_rows_and_reports_warnings():
    content = workbook_bytes(
        [
            HEADER,
            ["Acme", "India", "Pune", "March", 2025, "Cables", "M", 10, "1,250.50", "inr"],
            ["", "India", "Pune", "April", 2025, "Cables", "M", 10, 100, "INR"],  # no customer -> skipped
            ["Beta", None, None, 13, 2025, "Relays", None, None, 50, None],  # invalid month -> skipped
            ["Gamma", "UAE", "Dubai", 2, "2026", "Fans", "PCS", 3, 900, ""],  # no currency -> kept with warning
            [None] * 10,  # trailing blank row ignored
        ]
    )
    parsed = parse_sales_rows(read_xlsx(content, max_rows=100))
    assert [r["customerName"] for r in parsed.records] == ["Acme", "Gamma"]
    acme = parsed.records[0]
    assert acme["amount"] == 1250.5 and acme["currency"] == "INR" and acme["period"] == "2025-03" and acme["rowNumber"] == 2
    assert parsed.records[1]["currency"] == "N/A" and parsed.records[1]["period"] == "2026-02"
    messages = {w["row"]: w["message"] for w in parsed.warnings}
    assert messages[3] == "Skipped: customer name is empty."
    assert messages[4] == "Skipped: month/year is missing or invalid."
    assert "Currency is empty" in messages[5]
    assert len(parsed.rows) == 4  # trailing empty row dropped


def test_missing_columns_and_bad_files():
    with pytest.raises(SalesFileError, match="Missing required column"):
        parse_sales_rows([["Customer", "Something"], ["a", "b"]])
    with pytest.raises(SalesFileError, match="Unsupported file type"):
        read_xlsx(b"not a zip file", max_rows=10)
    with pytest.raises(SalesFileError, match="more than 2 rows"):
        read_xlsx(workbook_bytes([HEADER, *[["a"] * 10] * 5]), max_rows=2)


def test_date_column_is_accepted_instead_of_month_year():
    from datetime import datetime

    parsed = parse_sales_rows(
        read_xlsx(
            workbook_bytes(
                [
                    ["Dealer", "Item", "Revenue", "Invoice Date"],
                    ["Delta", "UPS", 10, datetime(2026, 5, 17)],
                ]
            ),
            max_rows=10,
        )
    )
    assert parsed.records[0]["period"] == "2026-05"


def test_sector_matching_matches_frontend_rules():
    assert product_matches_sub_sector("Breakers & Switches", "Switchgear")
    assert product_matches_sub_sector("Ring main unit (RMU)", "Switchgear")
    assert product_matches_sub_sector("UPS", "UPS")
    assert not product_matches_sub_sector("Groups", "UPS")  # whole words only
    assert matching_sub_sectors("Enclosures & Din Rail Products", ["Electrical Panels", "Electrical Accessories", "Fans"]) == [
        "Electrical Panels",
        "Electrical Accessories",
    ]


def test_rate_limiter_window():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("k") and limiter.allow("k")
    assert not limiter.allow("k")
    assert limiter.allow("other")


def test_storage_rejects_path_traversal(tmp_path):
    storage = LocalStorage(tmp_path)
    storage.save("a/b/file.txt", b"x")
    assert storage.read("a/b/file.txt") == b"x"
    with pytest.raises(ValueError):
        storage.save("../escape.txt", b"x")
    assert safe_file_name("..\\..\\etc/passwd") == "passwd"
    assert safe_file_name("report <final>.pdf") == "report _final_.pdf"
