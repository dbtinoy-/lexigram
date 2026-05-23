"""Tests for ProgressController (SSE streaming + status queries)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.progress import ProgressController
from lexigram.serialization import loads
from lexigram.tasks.progress import InMemoryProgressTracker


def _mock_request(task_id: str) -> Request:
    """Build a minimal Request stub with path_params."""
    req = MagicMock(spec=Request)
    req.path_params = {"task_id": task_id}
    return req


class TestProgressController:
    """Tests for ProgressController."""

    @pytest.fixture
    def controller(self) -> ProgressController:
        return ProgressController(tracker=InMemoryProgressTracker())

    @pytest.mark.asyncio
    async def test_status_unknown_task_404(
        self, controller: ProgressController
    ) -> None:
        result = await controller.get_task_status(_mock_request("missing"))
        assert result == ({"error": "Task not found"}, 404)

    @pytest.mark.asyncio
    async def test_status_running_task(self, controller: ProgressController) -> None:
        await controller.tracker.update("job-1", current=2, total=10, message="working")
        result = await controller.get_task_status(_mock_request("job-1"))
        assert isinstance(result, dict)
        assert result["id"] == "job-1"
        assert result["status"] == "running"
        assert result["progress"] == 20
        assert result["current"] == 2
        assert result["total"] == 10
        assert result["message"] == "working"
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_status_completed_task(self, controller: ProgressController) -> None:
        await controller.tracker.update("job-1", current=10, total=10)
        await controller.tracker.complete("job-1", result="done")
        result = await controller.get_task_status(_mock_request("job-1"))
        assert isinstance(result, dict)
        assert result["status"] == "complete"
        assert result["message"] == "done"

    @pytest.mark.asyncio
    async def test_stream_unknown_task_emits_error_event(
        self, controller: ProgressController
    ) -> None:
        response = await controller.stream_progress(_mock_request("missing"))
        body = "".join([chunk async for chunk in response.body_iterator])
        assert "event: error" in body
        assert "Task not found" in body

    @pytest.mark.asyncio
    async def test_stream_yields_updates_until_terminal(
        self, controller: ProgressController
    ) -> None:
        await controller.tracker.update("job-1", current=1, total=10)
        response = await controller.stream_progress(_mock_request("job-1"))
        task = asyncio.ensure_future(
            controller.tracker.complete("job-1", result="done")
        )
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

        parsed = [
            loads(line.split("data: ", 1)[1])
            for line in "\n".join(chunks).splitlines()
            if line.startswith("data: ")
        ]
        assert parsed[-1]["status"] == "complete"
        assert parsed[-1]["message"] == "done"

    def test_get_routes_include_progress_endpoints(
        self, controller: ProgressController
    ) -> None:
        paths = {route.path for route in controller.get_routes()}
        assert "/progress/{task_id}" in paths
        assert "/progress/{task_id}/stream" in paths
