"""R22 bulk-export regression tests (B28/B29).

See docs/09-01-2026/18-bulk-export-download.md. The toolbar export
buttons post ``action=export`` to the bulk route, which previously had no
export branch — the request fell through to ``"Unknown action: export"``
wrapped in a success toast, and no download ever happened.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from lexigram.admin.controllers.resource.bulk import ResourceBulkMixin
from lexigram.admin.controllers.resource.meta import ResourceMeta
from lexigram.serialization import loads_str


class _FakeResult:
    def __init__(self, items: list[Any]) -> None:
        self.items = items
        self.total = len(items)


class _FakeDataSource:
    """find_many-capable source over canned records."""

    def __init__(self, records: dict[str, Any]) -> None:
        self.records = records
        self.find_many_calls = 0
        self.find_one_calls = 0

    async def find_many(self, query: Any) -> _FakeResult:
        self.find_many_calls += 1
        return _FakeResult(list(self.records.values()))

    async def find_one(self, item_id: str) -> Any:
        self.find_one_calls += 1
        return self.records.get(item_id)


class _FindOneOnlySource:
    """Duck-typed source without find_many/QuerySpec support."""

    def __init__(self, records: dict[str, Any]) -> None:
        self.records = records

    async def find_one(self, item_id: str) -> Any:
        return self.records.get(item_id)


class _Controller(ResourceBulkMixin):
    def __init__(self, data_source: Any, *, enable_export: bool = True) -> None:
        self._ds = data_source
        self.meta = ResourceMeta(
            name="products",
            label="Product",
            label_plural="Products",
            prefix="/admin",
            enable_export=enable_export,
        )

    def get_data_source(self) -> Any:
        return self._ds


def _records() -> dict[str, Any]:
    return {
        "1": {"id": "1", "name": "Widget", "price": 10},
        "2": {"id": "2", "name": "=cmd|/c calc", "price": 20},
    }


class TestBulkExportCsv:
    async def test_returns_csv_attachment(self) -> None:
        ctl = _Controller(_FakeDataSource(_records()))
        response = await ctl.bulk_export(["1", "2"], "csv")
        assert response.status_code == 200
        assert response.media_type.startswith("text/csv")
        disposition = response.headers["content-disposition"]
        assert disposition.startswith('attachment; filename="products_export_')
        assert disposition.endswith('.csv"')
        assert response.headers["cache-control"] == "no-store"

        rows = list(csv.DictReader(io.StringIO(response.body.decode("utf-8"))))
        assert [r["name"] for r in rows] == ["Widget", "'=cmd|/c calc"]

    async def test_formula_injection_is_sanitized(self) -> None:
        ctl = _Controller(_FakeDataSource(_records()))
        response = await ctl.bulk_export(["2"], "csv")
        body = response.body.decode("utf-8")
        assert "'=cmd" in body  # sanitize_cell_value guard applied
        assert "\n=cmd" not in body

    async def test_selection_order_is_preserved(self) -> None:
        ctl = _Controller(_FakeDataSource(_records()))
        response = await ctl.bulk_export(["2", "1"], "csv")
        rows = list(csv.DictReader(io.StringIO(response.body.decode("utf-8"))))
        assert [r["id"] for r in rows] == ["2", "1"]

    async def test_find_one_fallback_for_duck_typed_sources(self) -> None:
        ctl = _Controller(_FindOneOnlySource(_records()))
        response = await ctl.bulk_export(["1"], "csv")
        rows = list(csv.DictReader(io.StringIO(response.body.decode("utf-8"))))
        assert [r["id"] for r in rows] == ["1"]

    async def test_object_rows_are_normalized(self) -> None:
        class _Row:
            def __init__(self) -> None:
                self.id = "9"
                self.name = "Obj"
                self._secret = "hidden"

        ctl = _Controller(_FindOneOnlySource({"9": _Row()}))
        response = await ctl.bulk_export(["9"], "csv")
        body = response.body.decode("utf-8")
        assert "Obj" in body
        assert "_secret" not in body
        assert "hidden" not in body


class TestBulkExportJson:
    async def test_returns_valid_json_array(self) -> None:
        ctl = _Controller(_FakeDataSource(_records()))
        response = await ctl.bulk_export(["1", "2"], "json")
        assert response.media_type == "application/json"
        data = loads_str(response.body.decode("utf-8"))
        assert isinstance(data, list)
        assert {row["id"] for row in data} == {"1", "2"}


class TestBulkExportGates:
    async def test_disabled_export_is_403(self) -> None:
        ctl = _Controller(_FakeDataSource(_records()), enable_export=False)
        response = await ctl.bulk_export(["1"], "csv")
        assert response.status_code == 403

    async def test_unsupported_format_is_400(self) -> None:
        # R29: xlsx became a supported direct-download format — pdf is the
        # remaining unsupported example.
        ctl = _Controller(_FakeDataSource(_records()))
        response = await ctl.bulk_export(["1"], "pdf")
        assert response.status_code == 400

    def test_export_actions_are_capability_gated_on_view(self) -> None:
        from lexigram.admin.controllers.resource.bulk import _EXPORT_BULK_ACTIONS

        assert set(_EXPORT_BULK_ACTIONS) == {
            "export",
            "export_csv",
            "export_json",
            "export_xlsx",
        }


_PKG_ROOT = Path(__file__).resolve().parents[3]


class TestB28FrontendHelperExists:
    def test_admin_js_defines_lexigram_download_bulk(self) -> None:
        """B28: buttons call window.LexigramDownloadBulk — it must exist."""
        js = (_PKG_ROOT / "src/lexigram/admin/static/js/admin.js").read_text(
            encoding="utf-8"
        )
        assert "window.LexigramDownloadBulk = function" in js
        assert "data-bulk-download-url" in js
        assert 'input[name="ids"]:checked' in js

    def test_layout_exposes_csrf_token_global(self) -> None:
        source = (
            _PKG_ROOT / "src/lexigram/admin/ui/layouts/admin_layout.py"
        ).read_text(encoding="utf-8")
        assert "window.__lexigramCsrfToken" in source
