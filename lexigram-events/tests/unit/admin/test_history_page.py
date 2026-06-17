"""Tests for the EventsHistoryPage admin page pagination."""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest

from lexigram.events.admin.pages import EventsHistoryPage


def _plain(html: str) -> str:
    """Strip tags so summary/pagination text can be asserted simply."""
    return re.sub(r"<[^>]+>", "", html)


class FakeRequest:
    """Minimal ASGI request stand-in with a URL path."""

    query_params: dict[str, str] = {}
    url = SimpleNamespace(path="/admin/events/history")

    @classmethod
    def with_params(cls, **params: str) -> FakeRequest:
        request = cls()
        request.query_params = params
        return request


class FakeStore:
    """Stub event store holding events in insertion (oldest-first) order."""

    def __init__(self, events: list[object]) -> None:
        self._events = events

    async def read_all(
        self, position: int = 0, count: int | None = None
    ) -> list[object]:
        if count is None:
            return list(self._events)
        return self._events[position : position + count]


def _event(i: int) -> object:
    return SimpleNamespace(
        event_id=f"event-{i}",
        occurred_at=f"2026-01-01T00:00:{i:02d}",
    )


class TestEventsHistoryPage:
    """Unit tests for the recent-events page renderer."""

    @pytest.mark.asyncio
    async def test_renders_newest_first_with_pagination(self) -> None:
        page = EventsHistoryPage(store=FakeStore([_event(i) for i in range(5)]))

        response = await page.handle(FakeRequest.with_params(per_page="2"))
        html = response.body.decode()

        assert "Showing 1 to 2 of 5 results" in _plain(html)
        assert 'hx-target="#table-data"' in html
        assert "event-4" in html
        assert "event-3" in html
        assert "event-0" not in html

    @pytest.mark.asyncio
    async def test_single_page_renders_summary(self) -> None:
        page = EventsHistoryPage(store=FakeStore([_event(i) for i in range(2)]))

        response = await page.handle(FakeRequest())
        html = response.body.decode()

        assert "Showing 1 to 2 of 2 results" in _plain(html)
        assert "event-1" in html
