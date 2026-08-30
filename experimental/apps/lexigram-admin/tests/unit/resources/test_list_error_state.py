"""List query failures must remain distinguishable from an empty result."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.list_query import ListDataFetcher
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.ui import TableState, render_to_string


class _BrokenResource:
    search_fields: list[str] = []

    async def fetch_list(self, **kwargs):
        raise RuntimeError("database details must not reach the browser")


class _LegacyService:
    def __init__(self) -> None:
        self.calls = 0

    async def list(self):
        self.calls += 1
        return [{"id": "legacy-1", "name": "Legacy"}]


class _LegacyResource(Resource):
    name = "legacy"
    model = None
    search_fields: list[str] = []


@pytest.mark.asyncio
async def test_resource_fetch_list_uses_legacy_service_resolver() -> None:
    service = _LegacyService()
    resource = _LegacyResource()
    resource.service = service

    items, total = await ListDataFetcher("legacy").fetch_data(
        SimpleNamespace(state=SimpleNamespace()),
        resource,
        TableState(),
        [],
    )

    assert items == [{"id": "legacy-1", "name": "Legacy"}]
    assert total == 1
    assert service.calls == 1


@pytest.mark.asyncio
async def test_fetcher_records_safe_error_for_table_state() -> None:
    fetcher = ListDataFetcher("widgets")
    items, total = await fetcher.fetch_data(
        SimpleNamespace(state=SimpleNamespace()),
        _BrokenResource(),
        TableState(),
        [],
    )

    assert items == []
    assert total == 0
    assert fetcher.error == "Failed to retrieve widgets items"


def test_data_table_renders_error_instead_of_empty_state() -> None:
    html = render_to_string(
        DataTable(
            data=[],
            state=TableState(),
            error="Failed to retrieve widgets items",
        )
    )

    assert "Failed to load data" in html
    assert "Failed to retrieve widgets items" in html
    assert "No results found" not in html
