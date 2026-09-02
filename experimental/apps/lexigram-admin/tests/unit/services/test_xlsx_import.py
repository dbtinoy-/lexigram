"""R26 Excel (.xlsx) import regression tests.

See docs/09-01-2026/22-xlsx-import.md. Workbook-building tests skip when
openpyxl is absent; the graceful-degradation tests run regardless.
"""

from __future__ import annotations

import io
from typing import Any

import pytest

import lexigram.admin.services.import_.service as import_service_module
from lexigram.admin.services.import_.service import AdminImportService


class _FakeDataSource:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        self.created.append(dict(data))
        return {"id": str(len(self.created)), **data}


def _service() -> AdminImportService:
    return AdminImportService(data_source=_FakeDataSource())


def _workbook_bytes(rows: list[list[Any]]) -> bytes:
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class TestXlsxParse:
    @pytest.mark.asyncio
    async def test_parses_rows_with_native_and_string_cells(self) -> None:
        content = _workbook_bytes(
            [
                ["name", "price", "active"],
                ["Widget", 10.5, True],
                ["  Gadget  ", 3, False],
            ]
        )
        result = await _service().parse(content, filename="products.xlsx")
        assert result.is_ok()
        job = result.unwrap()
        assert job.total_rows == 2
        # String cells stripped; numbers/booleans pass through natively.
        assert job.rows[0] == {"name": "Widget", "price": 10.5, "active": True}
        assert job.rows[1]["name"] == "Gadget"
        assert job.column_map == {
            "name": "name",
            "price": "price",
            "active": "active",
        }

    @pytest.mark.asyncio
    async def test_blank_rows_skipped_and_ragged_rows_fill_none(self) -> None:
        content = _workbook_bytes(
            [
                ["name", "sku"],
                ["Widget"],  # ragged — sku missing
                [None, None],  # fully blank — skipped
                ["", "   "],  # visually blank — skipped
                ["Gadget", "SKU-2"],
            ]
        )
        result = await _service().parse(content, filename="products.xlsx")
        job = result.unwrap()
        assert job.total_rows == 2
        assert job.rows[0] == {"name": "Widget", "sku": None}
        assert job.rows[1] == {"name": "Gadget", "sku": "SKU-2"}

    @pytest.mark.asyncio
    async def test_column_map_remaps_headers(self) -> None:
        content = _workbook_bytes(
            [
                ["Product Name", "Unit Price"],
                ["Widget", 10],
            ]
        )
        result = await _service().parse(
            content,
            filename="products.xlsx",
            column_map={"Product Name": "name", "Unit Price": "price"},
        )
        job = result.unwrap()
        assert job.rows == [{"name": "Widget", "price": 10}]

    @pytest.mark.asyncio
    async def test_unnamed_columns_are_ignored(self) -> None:
        content = _workbook_bytes(
            [
                ["name", None, "sku"],
                ["Widget", "noise", "SKU-1"],
            ]
        )
        result = await _service().parse(content, filename="products.xlsx")
        job = result.unwrap()
        assert job.rows == [{"name": "Widget", "sku": "SKU-1"}]

    @pytest.mark.asyncio
    async def test_corrupt_file_is_a_clean_error(self) -> None:
        result = await _service().parse(
            b"this is not a zip archive", filename="products.xlsx"
        )
        assert result.is_err()
        assert "Invalid Excel file" in str(result.unwrap_err().message)

    @pytest.mark.asyncio
    async def test_headerless_file_is_a_clean_error(self) -> None:
        content = _workbook_bytes([])
        result = await _service().parse(content, filename="products.xlsx")
        assert result.is_err()
        assert "no header row" in str(result.unwrap_err().message)


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_missing_openpyxl_yields_clean_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(import_service_module, "HAS_OPENPYXL", False)
        result = await _service().parse(b"irrelevant", filename="products.xlsx")
        assert result.is_err()
        message = str(result.unwrap_err().message)
        assert "openpyxl" in message
        assert "lexigram-admin[export]" in message

    @pytest.mark.asyncio
    async def test_unsupported_format_message_lists_xlsx(self) -> None:
        result = await _service().parse(b"x", filename="products.parquet")
        assert result.is_err()
        assert ".xlsx" in str(result.unwrap_err().message)


class TestAcceptDefaults:
    def test_import_action_accepts_xlsx(self) -> None:
        from lexigram.admin.actions.standard.imports import ImportAction

        assert ".xlsx" in ImportAction.DEFAULT_ACCEPT_EXTENSIONS

    def test_file_picker_default_accepts_xlsx(self) -> None:
        from lexigram.ui import render_to_string
        from lexigram.ui.molecules.data_table_client_logic import (
            DataTableScriptRenderer,
        )

        rendered = render_to_string(DataTableScriptRenderer.render([]))
        assert ".csv,.json,.jsonl,.xlsx" in rendered
