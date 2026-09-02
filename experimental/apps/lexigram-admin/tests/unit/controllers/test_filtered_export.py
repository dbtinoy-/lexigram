"""R25 filtered-dataset export regression tests (controller stack).

See docs/09-01-2026/21-filtered-export.md. With nothing selected, export
buttons forward ``scope=filtered`` + ``list_query`` and the server exports
every record matching the current list view.
"""

from __future__ import annotations

import csv
import io
from types import SimpleNamespace
from typing import Any

import pytest

from lexigram.admin.controllers.resource.bulk import (
    MAX_FILTERED_EXPORT_ROWS,
    ResourceBulkMixin,
)
from lexigram.admin.controllers.resource.list import ResourceListMixin
from lexigram.admin.controllers.resource.meta import ResourceMeta
from lexigram.admin.data.query_filters import FilterOperator


class _FakeResult:
    def __init__(self, items: list[Any], total: int) -> None:
        self.items = items
        self.total = total


class _QueryAwareSource:
    """find_many source that honors search/filters/sort/pagination."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records = records
        self.queries: list[Any] = []

    async def find_many(self, query: Any) -> _FakeResult:
        self.queries.append(query)
        items = list(self.records)
        if query.search:
            needle = query.search.lower()
            fields = query.search_fields or ["name"]
            items = [
                r
                for r in items
                if any(needle in str(r.get(f, "")).lower() for f in fields)
            ]
        for cond in query.where:
            if cond.operator == FilterOperator.EQ:
                items = [r for r in items if str(r.get(cond.field)) == str(cond.value)]
            elif cond.operator == FilterOperator.IN:
                wanted = {str(v) for v in cond.value}
                items = [r for r in items if str(r.get(cond.field)) in wanted]
        if query.sort_by:
            items.sort(
                key=lambda r: r.get(query.sort_by),
                reverse=query.sort_order == "desc",
            )
        total = len(items)
        start = (query.page - 1) * query.per_page
        return _FakeResult(items[start : start + query.per_page], total)


class _Controller(ResourceListMixin, ResourceBulkMixin):
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


class TestFilteredExport:
    @pytest.mark.asyncio
    async def test_exports_all_records_matching_filters(self) -> None:
        ctl = _Controller(_QueryAwareSource(_records()))
        response = await ctl.bulk_export_filtered("filter_status=active", "csv")
        assert response.status_code == 200
        rows = _csv_rows(response)
        # Meta default sort (id desc) applies — same ordering as the list.
        assert [r["id"] for r in rows] == ["5", "3", "1"]
        assert response.headers["cache-control"] == "no-store"

    @pytest.mark.asyncio
    async def test_search_is_forwarded(self) -> None:
        ds = _QueryAwareSource(_records())
        ctl = _Controller(ds)
        response = await ctl.bulk_export_filtered("q=Item+2", "csv")
        rows = _csv_rows(response)
        assert [r["id"] for r in rows] == ["2"]
        # Same search semantics as the list page (URLState -> _build_query).
        assert ds.queries[0].search == "Item 2"

    @pytest.mark.asyncio
    async def test_pages_beyond_the_visible_page(self) -> None:
        # 1500 matching records span two fetch pages of 1000.
        ds = _QueryAwareSource(
            [{"id": str(i), "name": "x", "status": "active"} for i in range(1500)]
        )
        ctl = _Controller(ds)
        response = await ctl.bulk_export_filtered("page=3&per_page=20", "csv")
        rows = _csv_rows(response)
        assert len(rows) == 1500  # not just the visible page of 20
        assert len(ds.queries) == 2

    @pytest.mark.asyncio
    async def test_row_cap_is_enforced(self) -> None:
        ds = _QueryAwareSource(
            [{"id": str(i), "name": "x"} for i in range(MAX_FILTERED_EXPORT_ROWS + 500)]
        )
        ctl = _Controller(ds)
        response = await ctl.bulk_export_filtered("", "csv")
        assert len(_csv_rows(response)) == MAX_FILTERED_EXPORT_ROWS

    @pytest.mark.asyncio
    async def test_export_disabled_is_403(self) -> None:
        ctl = _Controller(_QueryAwareSource(_records()), enable_export=False)
        response = await ctl.bulk_export_filtered("", "csv")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unsupported_format_is_400(self) -> None:
        ctl = _Controller(_QueryAwareSource(_records()))
        # R29: xlsx became a supported format — pdf remains unsupported.
        response = await ctl.bulk_export_filtered("", "pdf")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_oversized_list_query_is_400(self) -> None:
        ctl = _Controller(_QueryAwareSource(_records()))
        response = await ctl.bulk_export_filtered("q=" + "a" * 5000, "csv")
        assert response.status_code == 400


class TestBulkActionGating:
    def _request(self, form: dict[str, Any]) -> Any:
        class _Form(dict):
            def getlist(self, key: str) -> list[Any]:
                value = self.get(f"{key}__list", [])
                return list(value)

        return SimpleNamespace(
            scope={"admin_form_data": _Form(form)},
            headers={},
            state=SimpleNamespace(user=object(), permissions={"can_view": True}),
            query_params={},
        )

    @pytest.mark.asyncio
    async def test_idless_filtered_export_is_accepted(self) -> None:
        ctl = _Controller(_QueryAwareSource(_records()))
        request = self._request(
            {"action": "export", "scope": "filtered", "list_query": ""}
        )
        response = await ctl.bulk_action(request)
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_idless_export_without_scope_still_400(self) -> None:
        ctl = _Controller(_QueryAwareSource(_records()))
        response = await ctl.bulk_action(self._request({"action": "export"}))
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_idless_delete_still_400_even_with_scope(self) -> None:
        ctl = _Controller(_QueryAwareSource(_records()))
        response = await ctl.bulk_action(
            self._request({"action": "delete", "scope": "filtered"})
        )
        assert response.status_code == 400
