"""Progress tracking controller for SSE-based real-time updates."""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.admin.controllers.base import AdminController
from lexigram.contracts.infra.tasks.progress import (
    ProgressSnapshot,
    ProgressTrackerProtocol,
)
from lexigram.di.decorators import inject
from lexigram.serialization import dumps_str


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


@inject
class ProgressController(AdminController):
    """Controller for progress tracking endpoints.

    Exposes SSE streaming and point-in-time status queries backed by
    :class:`ProgressTrackerProtocol`.  Inject :class:`InMemoryProgressTracker`
    (or any conforming implementation) via the DI container.
    """

    def __init__(self, tracker: ProgressTrackerProtocol) -> None:
        super().__init__(prefix="/progress")  # type: ignore[call-arg]
        self.tracker = tracker

    def routes(self) -> None:
        """Define progress tracking routes."""
        from starlette.responses import StreamingResponse

        @self.router.get("/{task_id}/stream")  # type: ignore[attr-defined]
        async def stream_progress(task_id: str) -> StreamingResponse:
            """Stream progress updates via Server-Sent Events.

            The stream uses :meth:`ProgressTrackerProtocol.subscribe` so
            updates are pushed immediately rather than polled.  The generator
            closes automatically when the task reaches a terminal state.

            Args:
                task_id: Task identifier.

            Returns:
                SSE stream of progress snapshots.
            """

            async def event_generator() -> Any:
                try:
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

        @self.router.get("/{task_id}")  # type: ignore[attr-defined]
        async def get_task_status(
            task_id: str,
        ) -> dict[str, Any] | tuple[dict[str, str], int]:
            """Return current task status as a JSON dict.

            Args:
                task_id: Task identifier.

            Returns:
                Progress dict or a 404 error dict.
            """
            snap = await self.tracker.get(task_id)
            if snap is None:
                return {"error": "Task not found"}, 404
            return _snap_to_dict(snap)
