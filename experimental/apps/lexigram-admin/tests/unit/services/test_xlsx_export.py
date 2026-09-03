"""R29 regressions — Excel (.xlsx) direct-download export.

Covers:

* ``encode_rows_as_xlsx`` — round-trip, header/column-union behavior,
  formula sanitization, openpyxl type coercion (the JSON-column crash),
  missing-dependency ImportError.
* ``ExcelExportBackend`` — refactored onto the shared encoder; still
  uploads via storage and no longer crashes on dict/list cells.
* Controller stack — ``export_xlsx`` bulk action and ``format=xlsx``
  override produce an xlsx attachment; unsupported formats still 400.
* Handler stack — ``action=export_xlsx`` returns xlsx bytes with the
  download headers; missing openpyxl maps to 501 in both stacks.
"""

from __future__ import annotations

import io
from types import SimpleNamespace
from typing import Any

import pytest

from lexigram.admin.services.export import xlsx as xlsx_module
from lexigram.admin.services.export.xlsx import (
    XLSX_CONTENT_TYPE,
    coerce_cell_value,
    encode_rows_as_xlsx,
)


def read_sheet(payload: bytes) -> list[list[Any]]:
    """Load xlsx bytes and return all cell values row-wise."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(payload), read_only=True)
    ws = wb.active
    return [list(row) for row in ws.iter_rows(values_only=True)]


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------


class TestEncodeRowsAsXlsx:
    def test_roundtrip_headers_and_values(self):
        rows = [
            {"id": 1, "name": "Widget", "price": 9.5},
            {"id": 2, "name": "Gadget", "price": 19.0},
        ]
        sheet = read_sheet(encode_rows_as_xlsx(rows))
        assert sheet[0] == ["id", "name", "price"]
        assert sheet[1] == [1, "Widget", 9.5]
        assert sheet[2] == [2, "Gadget", 19.0]

    def test_column_union_across_ragged_rows(self):
        rows = [{"a": 1}, {"a": 2, "b": "late"}]
        sheet = read_sheet(encode_rows_as_xlsx(rows))
        assert sheet[0] == ["a", "b"]
        assert sheet[1] == [1, None]
        assert sheet[2] == [2, "late"]

    def test_explicit_fieldnames_control_order_and_subset(self):
        rows = [{"a": 1, "b": 2, "c": 3}]
        sheet = read_sheet(encode_rows_as_xlsx(rows, fieldnames=["c", "a"]))
        assert sheet[0] == ["c", "a"]
        assert sheet[1] == [3, 1]

    def test_formula_injection_sanitized(self):
        rows = [{"name": '=HYPERLINK("http://evil")', "note": "+SUM(A1)"}]
        sheet = read_sheet(encode_rows_as_xlsx(rows))
        assert sheet[1][0].startswith("'=")
        assert sheet[1][1].startswith("'+")

    def test_unstorable_types_coerced_not_crash(self):
        # Previously: openpyxl raised "Cannot convert ... to Excel".
        rows = [{"meta": {"k": "v"}, "tags": ["a", "b"], "blob": b"\xffraw"}]
        sheet = read_sheet(encode_rows_as_xlsx(rows))
        assert sheet[1][0] == str({"k": "v"})
        assert sheet[1][1] == str(["a", "b"])
        assert isinstance(sheet[1][2], str)

    def test_empty_rows_produce_valid_workbook(self):
        sheet = read_sheet(encode_rows_as_xlsx([]))
        assert sheet in ([], [[None]])  # empty sheet, no crash

    def test_missing_openpyxl_raises_import_error(self, monkeypatch):
        monkeypatch.setattr(xlsx_module, "HAS_OPENPYXL", False)
        with pytest.raises(ImportError, match="openpyxl"):
            encode_rows_as_xlsx([{"a": 1}])


class TestCoerceCellValue:
    def test_native_types_pass_through(self):
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        for value in ("s", 1, 1.5, True, None, now):
            assert coerce_cell_value(value) is value

    def test_bytes_decoded(self):
        assert coerce_cell_value(b"abc") == "abc"

    def test_objects_stringified(self):
        assert coerce_cell_value({"a": 1}) == "{'a': 1}"
        assert coerce_cell_value([1, 2]) == "[1, 2]"


# ---------------------------------------------------------------------------
# Backend (job flow) regression
# ---------------------------------------------------------------------------


class _MemoryStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def upload(self, path: str, data: bytes, content_type=None, **kw):
        self.files[path] = data


class TestExcelBackend:
    @pytest.mark.asyncio
    async def test_generate_file_uploads_valid_workbook(self):
        from lexigram.admin.services.export.adapters.excel import ExcelExportBackend

        storage = _MemoryStorage()
        job = SimpleNamespace(resource_name="products", columns=[])
        path = await ExcelExportBackend().generate_file(
            job,
            [{"id": 1, "attrs": {"color": "red"}}],  # dict cell must not crash
            storage,
            "exports",
        )
        assert path.startswith("exports/products_export_")
        assert path.endswith(".xlsx")
        sheet = read_sheet(storage.files[path])
        assert sheet[0] == ["id", "attrs"]
        assert sheet[1] == [1, str({"color": "red"})]


# ---------------------------------------------------------------------------
# Controller stack
# ---------------------------------------------------------------------------


class _FakeDataSource:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items

    async def find_many(self, query):
        return SimpleNamespace(items=list(self.items))

    async def find_one(self, item_id):
        for item in self.items:
            if str(item.get("id")) == str(item_id):
                return item
        return None


def make_controller(items: list[dict[str, Any]]):
    from lexigram.admin.controllers.resource.bulk import ResourceBulkMixin
    from lexigram.admin.controllers.resource.meta import ResourceMeta

    class Controller(ResourceBulkMixin):
        meta = ResourceMeta("products", "Product", "Products", prefix="/admin")

        def get_data_source(self):
            return _FakeDataSource(items)

    return Controller()


class TestControllerXlsxExport:
    @pytest.mark.asyncio
    async def test_bulk_export_xlsx(self):
        controller = make_controller(
            [{"id": "1", "name": "Widget"}, {"id": "2", "name": "Gadget"}]
        )
        resp = await controller.bulk_export(["1", "2"], "xlsx")
        assert resp.status_code == 200
        assert resp.media_type == XLSX_CONTENT_TYPE
        assert ".xlsx" in resp.headers["content-disposition"]
        assert resp.headers["cache-control"] == "no-store"
        sheet = read_sheet(resp.body)
        assert sheet[0] == ["id", "name"]
        assert sheet[1][1] == "Widget"

    @pytest.mark.asyncio
    async def test_unsupported_format_still_400(self):
        controller = make_controller([])
        resp = await controller.bulk_export(["1"], "pdf")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_export_xlsx_action_maps_to_xlsx_format(self):
        from lexigram.admin.controllers.resource.bulk import _EXPORT_BULK_ACTIONS

        assert _EXPORT_BULK_ACTIONS["export_xlsx"] == "xlsx"

    @pytest.mark.asyncio
    async def test_missing_openpyxl_maps_to_501(self, monkeypatch):
        monkeypatch.setattr(xlsx_module, "HAS_OPENPYXL", False)
        controller = make_controller([{"id": "1", "name": "W"}])
        resp = await controller.bulk_export(["1"], "xlsx")
        assert resp.status_code == 501
        assert b"openpyxl" in resp.body


# ---------------------------------------------------------------------------
# Handler stack
# ---------------------------------------------------------------------------


def make_resource_and_handler(items: list[dict[str, Any]]):
    from lexigram.admin.resources.base import Resource
    from lexigram.admin.resources.handler import BulkActionHandler

    class Products(Resource):
        name = "products"

    resource = Products()
    resource._data_source = _FakeDataSource(items)
    return resource, BulkActionHandler()


def make_bulk_request(form: dict[str, Any]) -> Any:
    from unittest.mock import MagicMock

    from starlette.requests import Request

    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": "/admin/products/bulk",
        "query_string": b"",
        "headers": [(b"hx-request", b"true")],
        "path_params": {},
        "app": None,
        "state": MagicMock(),
        "admin_resource_prefix": "products",
    }
    request = Request(scope)
    form_obj = MagicMock()
    form_obj.get = lambda key, default=None: form.get(key, default)
    form_obj.getlist = lambda key: form.get(f"{key}__list", [])
    request.scope["admin_form_data"] = form_obj
    return request


class TestHandlerXlsxExport:
    @pytest.mark.asyncio
    async def test_export_xlsx_returns_workbook_attachment(self):
        resource, handler = make_resource_and_handler(
            [{"id": "1", "name": "Widget", "attrs": {"c": "r"}}]
        )
        request = make_bulk_request({"action": "export_xlsx", "ids__list": ["1"]})
        resp = await handler.handle(request, resource)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/vnd.openxml")
        assert 'filename="products-export.xlsx"' in resp.headers["content-disposition"]
        assert resp.headers["cache-control"] == "no-store"
        assert resp.headers["hx-reswap"] == "none"
        sheet = read_sheet(resp.body)
        assert sheet[0] == ["id", "name", "attrs"]
        assert sheet[1][1] == "Widget"

    @pytest.mark.asyncio
    async def test_export_csv_unchanged(self):
        resource, handler = make_resource_and_handler([{"id": "1", "name": "W"}])
        request = make_bulk_request({"action": "export_csv", "ids__list": ["1"]})
        resp = await handler.handle(request, resource)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert ".csv" in resp.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_missing_openpyxl_maps_to_501(self, monkeypatch):
        monkeypatch.setattr(xlsx_module, "HAS_OPENPYXL", False)
        resource, handler = make_resource_and_handler([{"id": "1"}])
        request = make_bulk_request({"action": "export_xlsx", "ids__list": ["1"]})
        resp = await handler.handle(request, resource)
        assert resp.status_code == 501


# ---------------------------------------------------------------------------
# UI button renderers include export_xlsx
# ---------------------------------------------------------------------------


class TestDownloadButtonSets:
    def test_data_table_renderer_treats_export_xlsx_as_download(self):
        from lexigram.admin.ui.organisms.data_table.actions import (
            render_bulk_action_button,
        )

        action = SimpleNamespace(
            name="export_xlsx", label="Export Excel", icon=None, _color="secondary"
        )
        html = str(render_bulk_action_button(action, resource_prefix="/admin/products"))
        assert "LexigramDownloadBulk" in html
        assert 'data-bulk-action="export_xlsx"' in html
