"""Progress tracking controller for SSE-based real-time updates."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import StreamingResponse

from lexigram.admin.controllers.base import AdminController
from lexigram.contracts.infra.tasks.progress import (
    ProgressSnapshot,
    ProgressStatus,
    ProgressTrackerProtocol,
)
from lexigram.contracts.web import get
from lexigram.di.decorators import inject
from lexigram.serialization import dumps_str

if TYPE_CHECKING:
    from lexigram.admin.engine.renderer import AdminRenderer


def _snap_to_dict(snap: ProgressSnapshot) -> dict[str, Any]:
    """Convert a :class:`ProgressSnapshot` to a JSON-safe response dict."""
    return {
        "id": snap.task_id,
        "status": snap.status.value,
        "progress": snap.percent,
        "current": snap.current,
        "total": snap.total,
        "message": snap.message,
        "error": snap.error or None,
    }


class LocalProgressTracker:
    """In-process :class:`ProgressTrackerProtocol` implementation owned by lexigram-admin.

    Used as the DI-resolution fallback when no integrator (e.g. lexigram-tasks)
    has registered a real tracker — keeps :class:`ProgressController` mountable
    without a direct import of any sibling package. State is process-local and
    lost on restart, matching the previous `InMemoryProgressTracker` fallback's
    behavior.
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, ProgressSnapshot] = {}
        self._subscribers: dict[str, list[asyncio.Queue[ProgressSnapshot]]] = {}

    async def update(
        self, task_id: str, current: int, total: int, message: str = ""
    ) -> None:
        await self._publish(
            ProgressSnapshot(
                task_id=task_id,
                current=current,
                total=total,
                status=ProgressStatus.RUNNING,
                message=message,
            )
        )

    async def complete(self, task_id: str, result: str = "") -> None:
        prev = self._snapshots.get(task_id)
        await self._publish(
            ProgressSnapshot(
                task_id=task_id,
                current=prev.current if prev else 0,
                total=prev.total if prev else 0,
                status=ProgressStatus.COMPLETE,
                message=result,
            )
        )

    async def fail(self, task_id: str, error: str) -> None:
        prev = self._snapshots.get(task_id)
        await self._publish(
            ProgressSnapshot(
                task_id=task_id,
                current=prev.current if prev else 0,
                total=prev.total if prev else 0,
                status=ProgressStatus.FAILED,
                error=error,
            )
        )

    async def get(self, task_id: str) -> ProgressSnapshot | None:
        return self._snapshots.get(task_id)

    async def subscribe(self, task_id: str) -> AsyncIterator[ProgressSnapshot]:
        existing = self._snapshots.get(task_id)
        if existing is not None and existing.status in (
            ProgressStatus.COMPLETE,
            ProgressStatus.FAILED,
        ):
            yield existing
            return

        queue: asyncio.Queue[ProgressSnapshot] = asyncio.Queue()
        self._subscribers.setdefault(task_id, []).append(queue)
        try:
            while True:
                snap = await queue.get()
                yield snap
                if snap.status in (ProgressStatus.COMPLETE, ProgressStatus.FAILED):
                    return
        finally:
            self._subscribers.get(task_id, []).remove(queue)

    async def _publish(self, snap: ProgressSnapshot) -> None:
        self._snapshots[snap.task_id] = snap
        for queue in self._subscribers.get(snap.task_id, []):
            await queue.put(snap)


@inject
class ProgressController(AdminController):
    """Controller for progress tracking endpoints.

    Exposes SSE streaming and point-in-time status queries backed by
    :class:`ProgressTrackerProtocol`.  Inject :class:`LocalProgressTracker`
    (or any conforming implementation) via the DI container.
    """

    def __init__(
        self,
        tracker: ProgressTrackerProtocol,
        renderer: AdminRenderer | None = None,
    ) -> None:
        if renderer is None:
            from lexigram.admin.engine.renderer import AdminRenderer

            renderer = AdminRenderer()
        super().__init__(renderer=renderer)
        self.tracker = tracker

    @get("/progress/{task_id}/stream")
    async def stream_progress(self, request: Request) -> StreamingResponse:
        """Stream progress updates via Server-Sent Events.

        The stream uses :meth:`ProgressTrackerProtocol.subscribe` so
        updates are pushed immediately rather than polled.  The generator
        closes automatically when the task reaches a terminal state.

        Args:
            request: Starlette request.  The task id comes from the route.

        Returns:
            SSE stream of progress snapshots.
        """

        async def event_generator() -> Any:
            try:
                task_id = request.path_params["task_id"]
                # Guard: emit an error event and stop if the task is unknown.
                snap = await self.tracker.get(task_id)
                if snap is None:
                    yield (
                        f"event: error\ndata: "
                        f"{dumps_str({'error': 'Task not found'})}\n\n"
                    )
                    return

                # subscribe() yields until terminal state then closes.
                async for current_snap in self.tracker.subscribe(task_id):
                    yield (
                        f"event: progress\ndata: "
                        f"{dumps_str(_snap_to_dict(current_snap))}\n\n"
                    )

            except asyncio.CancelledError:
                # Client disconnected — clean exit.
                pass
            except (RuntimeError, ValueError, TypeError, OSError) as exc:
                yield f"event: error\ndata: {dumps_str({'error': str(exc)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    @get("/progress/{task_id}")
    async def get_task_status(
        self,
        request: Request,
    ) -> dict[str, Any] | tuple[dict[str, str], int]:
        """Return current task status as a JSON dict.

        Args:
            request: Starlette request.  The task id comes from the route.

        Returns:
            Progress dict or a 404 error dict.
        """
        task_id = request.path_params["task_id"]
        snap = await self.tracker.get(task_id)
        if snap is None:
            return {"error": "Task not found"}, 404
        return _snap_to_dict(snap)
