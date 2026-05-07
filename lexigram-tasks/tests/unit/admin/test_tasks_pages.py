"""Tests for the task admin pages pagination."""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest

from lexigram.tasks.admin.pages import TasksFailedPage, TasksHistoryPage
from lexigram.tasks.models import JobResult
from lexigram.tasks.results import InMemoryResultStore


def _plain(html: str) -> str:
    """Strip tags so summary/pagination text can be asserted simply."""
    return re.sub(r"<[^>]+>", "", html)


class FakeRequest:
    """Minimal ASGI request stand-in with a URL path."""

    query_params: dict[str, str] = {}
    url = SimpleNamespace(path="/admin/tasks")

    @classmethod
    def with_params(cls, path: str, **params: str) -> FakeRequest:
        """Build a request whose path and query params are set explicitly."""
        request = cls()
        request.url = SimpleNamespace(path=path)
        request.query_params = params
        return request


class TestTasksHistoryPage:
    """Unit tests for the completed-tasks history page."""

    @pytest.mark.asyncio
    async def test_renders_completed_tasks_newest_first(self) -> None:
        """Completed results render newest first with a summary."""
        store = InMemoryResultStore()
        for i in range(3):
            await store.store(
                f"job-{i}",
                JobResult(success=True, id=f"job-{i}", name=f"task-{i}"),
            )

        page = TasksHistoryPage(result_store=store)
        response = await page.handle(FakeRequest.with_params("/admin/tasks/history"))
        html = response.body.decode()

        assert "job-2" in html
        assert "task-0" in html
        assert "Showing 1 to 3 of 3 results" in _plain(html)

    @pytest.mark.asyncio
    async def test_renders_pagination_when_many(self) -> None:
        """Pagination controls and slicing render when data spills pages."""
        store = InMemoryResultStore()
        for i in range(5):
            await store.store(
                f"job-{i}",
                JobResult(success=True, id=f"job-{i}", name=f"task-{i}"),
            )

        page = TasksHistoryPage(result_store=store)
        response = await page.handle(
            FakeRequest.with_params("/admin/tasks/history", per_page="2")
        )
        html = response.body.decode()

        assert "Showing 1 to 2 of 5 results" in _plain(html)
        assert 'hx-target="#table-data"' in html
        assert "job-4" in html
        assert "job-3" in html
        assert "job-0" not in html

    @pytest.mark.asyncio
    async def test_out_of_range_page_clamps_to_last(self) -> None:
        """Pages past the last page clamp to the final slice."""
        store = InMemoryResultStore()
        for i in range(5):
            await store.store(
                f"job-{i}",
                JobResult(success=True, id=f"job-{i}", name=f"task-{i}"),
            )

        page = TasksHistoryPage(result_store=store)
        response = await page.handle(
            FakeRequest.with_params("/admin/tasks/history", page="99", per_page="2")
        )
        html = response.body.decode()

        assert "Showing 5 to 5 of 5 results" in _plain(html)
        assert "job-0" in html


class TestTasksFailedPage:
    """Unit tests for the failed-tasks page."""

    @pytest.mark.asyncio
    async def test_renders_failed_tasks_with_error_and_pagination(self) -> None:
        """Failed results show their error and honour pagination."""
        store = InMemoryResultStore()
        for i in range(5):
            await store.store(
                f"job-{i}",
                JobResult(
                    success=False,
                    id=f"job-{i}",
                    name=f"task-{i}",
                    error=f"boom-{i}",
                ),
            )

        page = TasksFailedPage(result_store=store)
        response = await page.handle(
            FakeRequest.with_params("/admin/tasks/failed", per_page="2")
        )
        html = response.body.decode()

        assert "Showing 1 to 2 of 5 results" in _plain(html)
        assert 'hx-target="#table-data"' in html
        assert "boom-4" in html
        assert "boom-0" not in html
