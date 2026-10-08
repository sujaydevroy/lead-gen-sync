"""Dealer upload: file reading (csv / xlsx), header matching and cell parsing (no database)."""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

import pytest
from openpyxl import Workbook

from app.core.errors import ApiError
from app.services.dealer_import_service import RowError, _amount, _date, _products, map_columns
from app.services.tabular_reader import read_table


def test_header_matching_is_loose_and_reports_unknown_columns():
    mapping, ignored = map_columns(["DEALER NAME", "dealer_id", "Zip Code", "E-mail", "Dealer Name", "Comments", ""])
    assert mapping == {"dealer_name": 0, "dealer_code": 1, "postal_code": 2, "email": 3}
    assert ignored == ["Dealer Name", "Comments"]  # a second "Dealer Name" column is not used


def test_cell_parsing():
    assert _date("2026-09-01", "Date") == date(2026, 9, 1)
    assert _date("01/09/2026", "Date") == date(2026, 9, 1)  # day first
    assert _date("Not Available", "Date") is None
    with pytest.raises(RowError):
        _date("31/13/2026", "Date")
    assert _amount("1,250.505") == Decimal("1250.51")
    assert _amount(42) == Decimal("42.00")
    with pytest.raises(RowError):
        _amount("abc")
    assert _products("MCB; Switchgear | mcb, Cables\nPanels") == ["MCB", "Switchgear", "Cables", "Panels"]


def test_read_csv_variants():
    table = read_table("﻿Dealer Name\tCountry\n\nA\tIndia\nB\tJapan\n".encode(), "x.csv")
    assert table.file_format == "csv" and table.headers == ["Dealer Name", "Country"]
    assert table.rows == [(3, ["A", "India"]), (4, ["B", "Japan"])]  # blank line skipped, row numbers kept
    with pytest.raises(ApiError) as error:
        read_table(b"", "x.csv")
    assert error.value.status_code == 422
    with pytest.raises(ApiError) as error:
        read_table(b"abc", "x.txt")
    assert error.value.status_code == 415


def test_read_xlsx_with_wrong_extension_and_row_limit():
    book = Workbook()
    for row in (["Dealer Name", "Phone"], ["A", 9811122233.0], ["B", None]):
        book.active.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    table = read_table(buffer.getvalue(), "saved-as.xls")  # content wins over the extension
    assert table.file_format == "xlsx" and table.rows[0] == (2, ["A", 9811122233])
    with pytest.raises(ApiError):
        read_table(buffer.getvalue(), "x.xlsx", max_rows=1)
