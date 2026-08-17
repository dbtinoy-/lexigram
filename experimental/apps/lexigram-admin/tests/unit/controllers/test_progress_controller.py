"""Tests for ProgressController (SSE streaming + status queries)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.progress import LocalProgressTracker, ProgressController
from lexigram.contracts.infra.tasks.progress import ProgressTrackerProtocol
from lexigram.serialization import loads
from lexigram.tasks.progress import InMemoryProgressTracker


class TestLocalProgressTracker:
    """Tests for the admin-owned ProgressTrackerProtocol fallback implementation."""

    def test_conforms_to_protocol(self) -> None:
        assert isinstance(LocalProgressTracker(), ProgressTrackerProtocol)

    @pytest.mark.asyncio
    async def test_get_unknown_task_returns_none(self) -> None:
        tracker = LocalProgressTracker()
        assert await tracker.get("missing") is None

    @pytest.mark.asyncio
    async def test_update_then_get_returns_snapshot(self) -> None:
        tracker = LocalProgressTracker()
        await tracker.update("job-1", current=3, total=10, message="working")
        snap = await tracker.get("job-1")
        assert snap is not None
        assert snap.current == 3
        assert snap.total == 10
        assert snap.message == "working"
        assert snap.status.value == "running"

    @pytest.mark.asyncio
    async def test_complete_sets_terminal_status(self) -> None:
        tracker = LocalProgressTracker()
        await tracker.update("job-1", current=10, total=10)
        await tracker.complete("job-1", result="done")
        snap = await tracker.get("job-1")
        assert snap is not None
        assert snap.status.value == "complete"
        assert snap.message == "done"

    @pytest.mark.asyncio
    async def test_fail_sets_terminal_status_with_error(self) -> None:
        tracker = LocalProgressTracker()
        await tracker.update("job-1", current=1, total=10)
        await tracker.fail("job-1", error="boom")
        snap = await tracker.get("job-1")
        assert snap is not None
        assert snap.status.value == "failed"
        assert snap.error == "boom"

    @pytest.mark.asyncio
    async def test_subscribe_receives_live_updates_and_stops_on_terminal(self) -> None:
        tracker = LocalProgressTracker()

        async def producer() -> None:
            await tracker.update("job-1", current=1, total=2)
            await tracker.update("job-1", current=2, total=2)
            await tracker.complete("job-1", result="done")

        received = []

        async def consume() -> None:
            async for snap in tracker.subscribe("job-1"):
                received.append(snap)

        producer_task = asyncio.ensure_future(producer())
        await consume()
        await producer_task

        assert [s.current for s in received] == [1, 2, 2]
        assert received[-1].status.value == "complete"

    @pytest.mark.asyncio
    async def test_subscribe_on_already_terminal_task_yields_once(self) -> None:
        tracker = LocalProgressTracker()
        await tracker.update("job-1", current=1, total=1)
        await tracker.complete("job-1")

        received = [snap async for snap in tracker.subscribe("job-1")]
        assert len(received) == 1
        assert received[0].status.value == "complete"


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
