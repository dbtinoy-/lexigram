"""R25 filtered-dataset export regression tests (declarative handler stack).

See docs/09-01-2026/21-filtered-export.md.
"""

from __future__ import annotations

import csv
import io
from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.handler import BulkActionHandler


class _FakeDataSource:
    def __init__(self, records: dict[str, dict[str, Any]]) -> None:
        self._store = records

    async def find_one(self, item_id: Any) -> dict[str, Any] | None:
        return self._store.get(str(item_id))


class _Items(Resource):
    name = "items"

    #: (kwargs of every fetch_list call) — lets tests assert forwarding.
    fetch_calls: list[dict[str, Any]]

    def columns(self) -> list[str]:  # allowlisted fields
        return ["id", "name", "status"]

    async def fetch_list(self, **kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        self.fetch_calls.append(dict(kwargs))
        items = list(self._all_records)
        search = kwargs.get("search")
        if search:
            needle = str(search).lower()
            items = [r for r in items if needle in str(r.get("name", "")).lower()]
        for field, value in (kwargs.get("filters") or {}).items():
            items = [r for r in items if str(r.get(field)) == str(value)]
        sort_by = kwargs.get("sort_by")
        if sort_by:
            items.sort(
                key=lambda r: r.get(sort_by),
                reverse=kwargs.get("sort_order") == "desc",
            )
        total = len(items)
        offset = int(kwargs.get("offset") or 0)
        limit = int(kwargs.get("limit") or len(items))
        return items[offset : offset + limit], total


def _resource(records: list[dict[str, Any]]) -> _Items:
    resource = _Items()
    resource._all_records = records
    resource.fetch_calls = []
    resource._data_source = _FakeDataSource({str(r["id"]): r for r in records})
    return resource


def _request(form: dict[str, Any]) -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": "/admin/items/bulk",
        "query_string": b"",
        "headers": [],
        "path_params": {},
        "app": None,
        "state": MagicMock(),
        "admin_resource_prefix": "items",
    }
    request = Request(scope)
    form_obj = MagicMock()
    form_obj.get = lambda key, default=None: form.get(key, default)
    form_obj.getlist = lambda key: form.get(f"{key}__list", [])
    request.scope["admin_form_data"] = form_obj
    return request


def _records(count: int = 5) -> list[dict[str, Any]]:
    return [
        {
            "id": str(i),
            "name": f"Item {i}",
            "status": "active" if i % 2 else "archived",
        }
        for i in range(1, count + 1)
    ]


def _csv_rows(response: Any) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(response.body.decode("utf-8"))))


class TestHandlerFilteredExport:
    @pytest.mark.asyncio
    async def test_filtered_export_returns_matching_records(self) -> None:
        resource = _resource(_records())
        handler = BulkActionHandler()
        response = await handler.handle(
            _request(
                {
                    "action": "export",
                    "scope": "filtered",
                    "list_query": "filter_status=active",
                }
            ),
            resource,
        )
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")
        assert response.headers.get("cache-control") == "no-store"
        rows = _csv_rows(response)
        assert [r["id"] for r in rows] == ["1", "3", "5"]
        # The list page's filter semantics were forwarded to fetch_list.
        assert resource.fetch_calls[0]["filters"] == {"status": "active"}

    @pytest.mark.asyncio
    async def test_search_is_forwarded(self) -> None:
        resource = _resource(_records())
        handler = BulkActionHandler()
        response = await handler.handle(
            _request(
                {"action": "export", "scope": "filtered", "list_query": "search=Item 2"}
            ),
            resource,
        )
        rows = _csv_rows(response)
        assert [r["id"] for r in rows] == ["2"]

    @pytest.mark.asyncio
    async def test_pages_beyond_the_visible_page(self) -> None:
        resource = _resource(
            [{"id": str(i), "name": "x", "status": "active"} for i in range(1500)]
        )
        handler = BulkActionHandler()
        response = await handler.handle(
            _request(
                {
                    "action": "export",
                    "scope": "filtered",
                    "list_query": "page=3&per_page=20",
                }
            ),
            resource,
        )
        assert len(_csv_rows(response)) == 1500
        assert len(resource.fetch_calls) == 2  # two pages of 1000

    @pytest.mark.asyncio
    async def test_unknown_sort_field_is_dropped(self) -> None:
        resource = _resource(_records())
        handler = BulkActionHandler()
        response = await handler.handle(
            _request(
                {
                    "action": "export",
                    "scope": "filtered",
                    "list_query": "sort_by=__proto__",
                }
            ),
            resource,
        )
        assert response.status_code == 200
        assert resource.fetch_calls[0]["sort_by"] is None

    @pytest.mark.asyncio
    async def test_idless_export_without_scope_still_400(self) -> None:
        resource = _resource(_records())
        handler = BulkActionHandler()
        response = await handler.handle(
            _request({"action": "export"}),
            resource,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_idless_delete_still_400_even_with_scope(self) -> None:
        resource = _resource(_records())
        handler = BulkActionHandler()
        response = await handler.handle(
            _request({"action": "delete", "scope": "filtered"}),
            resource,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_fetch_failure_returns_503_not_empty_file(self) -> None:
        resource = _resource(_records())

        async def _boom(**kwargs: Any) -> tuple[list[Any], int]:
            raise RuntimeError("storage exploded")

        resource.fetch_list = _boom  # type: ignore[method-assign]
        handler = BulkActionHandler()
        response = await handler.handle(
            _request({"action": "export", "scope": "filtered", "list_query": ""}),
            resource,
        )
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_selected_ids_export_unchanged(self) -> None:
        resource = _resource(_records())
        handler = BulkActionHandler()
        response = await handler.handle(
            _request({"action": "export", "ids__list": ["2", "4"]}),
            resource,
        )
        rows = _csv_rows(response)
        assert [r["id"] for r in rows] == ["2", "4"]


class TestClientScriptsCarryFilteredExport:
    def test_admin_js_forwards_scope_and_list_query(self) -> None:
        from pathlib import Path

        js = Path("src/lexigram/admin/static/js/admin.js").read_text("utf-8")
        assert "scope', 'filtered'" in js.replace('"', "'")
        assert "list_query" in js
        assert "Select at least one row to export" not in js

    def test_inline_script_forwards_scope_and_list_query(self) -> None:
        from lexigram.ui import render_to_string
        from lexigram.ui.molecules.data_table_client_logic import (
            DataTableScriptRenderer,
        )

        rendered = render_to_string(DataTableScriptRenderer.render([]))
        assert "'scope', 'filtered'" in rendered.replace('"', "'")
        assert "list_query" in rendered
        assert "Select at least one record." not in rendered
