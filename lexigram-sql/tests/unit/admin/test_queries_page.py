"""Tests for the SqlQueriesPage admin page pagination."""

from __future__ import annotations

from datetime import datetime
import re
from types import SimpleNamespace

import pytest

from lexigram.contracts.data.sql.query_log import QueryLogEntry
from lexigram.sql.admin.pages import SqlQueriesPage


def _plain(html: str) -> str:
    """Strip tags so summary/pagination text can be asserted simply."""
    return re.sub(r"<[^>]+>", "", html)


class FakeRequest:
    """Minimal ASGI request stand-in with a URL path."""

    query_params: dict[str, str] = {}
    url = SimpleNamespace(path="/admin/sql/queries")


class FakeQueryLogger:
    """Stub query logger returning a fixed set of entries."""

    def __init__(self, entries: list[QueryLogEntry]) -> None:
        self._entries = entries

    async def get_recent_queries(self, limit: int = 100) -> list[QueryLogEntry]:
        """Return the most recent entries, honouring *limit*."""
        return self._entries[-limit:]


def _entry(i: int) -> QueryLogEntry:
    return QueryLogEntry(
        sql=f"SELECT {i}",
        execution_time=0.01 * i,
        timestamp=datetime(2026, 1, 1, 0, 0, i),
    )


class TestSqlQueriesPage:
    """Unit tests for the recent-queries page renderer."""

    @pytest.mark.asyncio
    async def test_renders_pagination_when_many_entries(self) -> None:
        logger = FakeQueryLogger([_entry(i) for i in range(5)])
        page = SqlQueriesPage(query_logger=logger)

        request = FakeRequest()
        request.query_params = {"per_page": "2"}
        response = await page.handle(request)
        html = response.body.decode()

        assert "Showing 1 to 2 of 5 results" in _plain(html)
        assert 'hx-target="#table-data"' in html
        assert "SELECT 0" in html
        assert "SELECT 1" in html
        assert "SELECT 4" not in html

    @pytest.mark.asyncio
    async def test_second_page_slices_offsets(self) -> None:
        logger = FakeQueryLogger([_entry(i) for i in range(5)])
        page = SqlQueriesPage(query_logger=logger)

        request = FakeRequest()
        request.query_params = {"page": "2", "per_page": "2"}
        response = await page.handle(request)
        html = response.body.decode()

        assert "Showing 3 to 4 of 5 results" in _plain(html)
        assert "SELECT 2" in html
        assert "SELECT 3" in html
        assert "SELECT 1" not in html

    @pytest.mark.asyncio
    async def test_single_page_renders_summary(self) -> None:
        logger = FakeQueryLogger([_entry(i) for i in range(2)])
        page = SqlQueriesPage(query_logger=logger)

        response = await page.handle(FakeRequest())
        html = response.body.decode()

        assert "Showing 1 to 2 of 2 results" in _plain(html)
        assert "SELECT 0" in html

    @pytest.mark.asyncio
    async def test_out_of_range_page_clamps_to_last(self) -> None:
        logger = FakeQueryLogger([_entry(i) for i in range(3)])
        page = SqlQueriesPage(query_logger=logger)

        request = FakeRequest()
        request.query_params = {"page": "99", "per_page": "2"}
        response = await page.handle(request)
        html = response.body.decode()

        assert "Showing 3 to 3 of 3 results" in _plain(html)
        assert "SELECT 2" in html
        assert "SELECT 0" not in html
