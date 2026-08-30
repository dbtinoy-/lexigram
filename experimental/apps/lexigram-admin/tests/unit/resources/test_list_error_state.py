"""List query failures must remain distinguishable from an empty result."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lexigram.admin.resources.list_query import ListDataFetcher
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.ui import TableState, render_to_string


class _BrokenResource:
    search_fields: list[str] = []

    async def fetch_list(self, **kwargs):
        raise RuntimeError("database details must not reach the browser")


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
