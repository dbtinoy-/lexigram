"""Progress tracking controller for SSE-based real-time updates."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
import hmac
from typing import TYPE_CHECKING, Any
from uuid import UUID

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


_TERMINAL_STATUSES = (ProgressStatus.COMPLETE, ProgressStatus.FAILED)


def _snap_to_dict(snap: ProgressSnapshot) -> dict[str, Any]:
    """Convert a :class:`ProgressSnapshot` to a JSON-safe response dict."""
    metadata = getattr(snap, "metadata", {})
    return {
        "id": snap.task_id,
        "status": snap.status.value,
        "progress": snap.percent,
        "current": snap.current,
        "total": snap.total,
        "message": snap.message,
        "error": snap.error or None,
        # Older third-party snapshots do not have metadata. Keep the wire
        # shape stable and never expose a mutable tracker-owned dictionary.
        "metadata": dict(metadata) if isinstance(metadata, Mapping) else {},
    }


def _identity_text(value: Any) -> str | None:
    """Normalize only scalar identity values into a stable registry key."""
    if isinstance(value, bool) or not isinstance(value, (str, int, UUID)):
        return None
    normalized = str(value).strip()
    return normalized or None


def _value_from_identity(source: Any) -> str | None:
    """Read a stable identity value from a mapping or user-like object."""
    keys = (
        "id",
        "user_id",
        "admin_user_id",
        "uuid",
        "username",
        "email",
        "csrf_session_id",
    )
    if isinstance(source, Mapping):
        for key in keys:
            value = _identity_text(source.get(key))
            if value is not None:
                return value
        return None
    scalar = _identity_text(source)
    if scalar is not None:
        return scalar
    for key in keys:
        try:
            value = _identity_text(getattr(source, key, None))
        except Exception:  # noqa: BLE001 — identity lookup must fail closed
            value = None
        if value is not None:
            return value
    return None


def progress_principal_key(request: Any) -> str | None:
    """Return a stable, non-secret principal key for a progress request.

    Authenticated user ids are preferred. A session id is a useful fallback
    for deployments whose auth middleware stores only a session principal in
    the request. ``None`` means there is no identity to bind a background task
    to, so callers should keep the operation synchronous.
    """
    try:
        state = request.state
        user = getattr(state, "user", None)
        value = _value_from_identity(user)
        if value is None:
            value = _value_from_identity(getattr(state, "user_id", None))
        if value is not None:
            return f"user:{value}"
    except (AttributeError, KeyError, RuntimeError):
        pass

    # Accessing Request.session without SessionMiddleware raises an assertion;
    # inspect the scope first so minimal/unit requests remain safe.
    scope = getattr(request, "scope", None)
    session: Mapping[str, Any] | None = None
    if isinstance(scope, Mapping) and isinstance(scope.get("session"), Mapping):
        session = scope["session"]
    if session is None:
        try:
            candidate = request.session
            if isinstance(candidate, Mapping):
                session = candidate
        except (AttributeError, AssertionError, KeyError, RuntimeError):
            session = None
    if session is not None:
        value = _value_from_identity(
            {
                key: session.get(key)
                for key in ("admin_user_id", "user_id", "csrf_session_id")
            }
        )
        if value is not None:
            return f"session:{value}"
    return None


class ProgressAccessRegistry:
    """Bounded in-process owner registry for admin-created progress tasks.

    Progress ids are cryptographically random, but randomness alone is not an
    authorization boundary. This registry binds ids created by the bulk
    endpoint to the principal that submitted them. Tasks not registered here
    remain readable for compatibility with pre-existing generic task producers;
    those producers can opt into the same registry when they need ownership
    isolation.
    """

    def __init__(self, max_entries: int = 4096) -> None:
        self._owners: dict[str, str] = {}
        self._max_entries = max(1, int(max_entries))

    def register(self, task_id: str, owner_key: str) -> bool:
        """Register a task owner, refusing an attempted owner replacement."""
        task_id = str(task_id)
        owner_key = str(owner_key)
        if not task_id or not owner_key:
            return False
        existing = self._owners.get(task_id)
        if existing is not None:
            return hmac.compare_digest(existing, owner_key)
        # Never evict an owner silently: doing so would downgrade an existing
        # task to the compatibility path and make it readable by another
        # principal. Once the bounded registry is full, callers fall back to
        # their synchronous operation instead.
        if len(self._owners) >= self._max_entries:
            return False
        self._owners[task_id] = owner_key
        return True

    def unregister(self, task_id: str) -> None:
        """Remove an owner binding when task creation fails before dispatch."""
        self._owners.pop(str(task_id), None)

    def is_allowed(self, task_id: str, owner_key: str | None) -> bool:
        """Return whether ``owner_key`` may read the task.

        Unknown registry entries are allowed for backwards compatibility with
        tasks created outside the admin bulk endpoint. Registered tasks require
        a matching non-empty principal key.
        """
        owner = self._owners.get(str(task_id))
        if owner is None:
            return True
        return owner_key is not None and hmac.compare_digest(owner, owner_key)


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

    async def complete(
        self,
        task_id: str,
        result: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        existing = self._snapshots.get(task_id)
        await self._publish(
            ProgressSnapshot(
                task_id=task_id,
                current=existing.total if existing else 0,
                total=existing.total if existing else 0,
                status=ProgressStatus.COMPLETE,
                message=result,
                metadata=dict(metadata or {}),
            )
        )

    async def fail(
        self,
        task_id: str,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        existing = self._snapshots.get(task_id)
        await self._publish(
            ProgressSnapshot(
                task_id=task_id,
                current=existing.current if existing else 0,
                total=existing.total if existing else 0,
                status=ProgressStatus.FAILED,
                error=error,
                metadata=dict(metadata or {}),
            )
        )

    async def get(self, task_id: str) -> ProgressSnapshot | None:
        return self._snapshots.get(task_id)

    async def subscribe(self, task_id: str) -> AsyncIterator[ProgressSnapshot]:
        existing = self._snapshots.get(task_id)
        if existing is not None and existing.status in _TERMINAL_STATUSES:
            yield existing
            return

        queue: asyncio.Queue[ProgressSnapshot] = asyncio.Queue()
        self._subscribers.setdefault(task_id, []).append(queue)
        try:
            while True:
                snap = await queue.get()
                yield snap
                if snap.status in _TERMINAL_STATUSES:
                    return
        finally:
            subscribers = self._subscribers.get(task_id, [])
            try:
                subscribers.remove(queue)
            except ValueError:
                pass
            if not subscribers:
                self._subscribers.pop(task_id, None)

    async def _publish(self, snap: ProgressSnapshot) -> None:
        self._snapshots[snap.task_id] = snap
        for queue in self._subscribers.get(snap.task_id, []):
            await queue.put(snap)


@inject
class ProgressController(AdminController):
    """Controller for progress tracking endpoints.

    Exposes SSE streaming and point-in-time status queries backed by
    :class:`ProgressTrackerProtocol`. Inject ``LocalProgressTracker`` (or any
    conforming implementation) via the DI container.
    """

    def __init__(
        self,
        tracker: ProgressTrackerProtocol,
        renderer: AdminRenderer | None = None,
        access_registry: ProgressAccessRegistry | None = None,
    ) -> None:
        if renderer is None:
            from lexigram.admin.engine.renderer import AdminRenderer

            renderer = AdminRenderer()
        super().__init__(renderer=renderer)
        self.tracker = tracker
        self.access_registry = access_registry or ProgressAccessRegistry()

    def _allowed(self, request: Request, task_id: str) -> bool:
        """Check task ownership without revealing whether an id exists."""
        return self.access_registry.is_allowed(task_id, progress_principal_key(request))

    @staticmethod
    def _not_found_stream() -> StreamingResponse:
        """Return an SSE-shaped 404 without disclosing task existence."""

        async def event_generator() -> AsyncIterator[str]:
            yield f"event: error\ndata: {dumps_str({'error': 'Task not found'})}\n\n"

        return StreamingResponse(
            event_generator(),
            status_code=404,
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @get("/progress/{task_id}/stream")
    async def stream_progress(self, request: Request) -> StreamingResponse:
        """Stream progress updates via Server-Sent Events."""
        task_id = str(request.path_params["task_id"])
        if not self._allowed(request, task_id):
            return self._not_found_stream()
        try:
            snap = await self.tracker.get(task_id)
        except (RuntimeError, ValueError, TypeError, OSError):
            return self._not_found_stream()
        if snap is None:
            return self._not_found_stream()

        async def event_generator() -> AsyncIterator[str]:
            try:
                # subscribe() yields until terminal state then closes.
                async for current_snap in self.tracker.subscribe(task_id):
                    yield (
                        f"event: progress\ndata: "
                        f"{dumps_str(_snap_to_dict(current_snap))}\n\n"
                    )
            except asyncio.CancelledError:
                # Client disconnected — clean exit.
                pass
            except (RuntimeError, ValueError, TypeError, OSError):
                # Do not include tracker internals in the stream.
                yield f"event: error\ndata: {dumps_str({'error': 'Progress stream unavailable'})}\n\n"

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
        """Return current task status as a JSON dict."""
        task_id = str(request.path_params["task_id"])
        if not self._allowed(request, task_id):
            return {"error": "Task not found"}, 404
        snap = await self.tracker.get(task_id)
        if snap is None:
            return {"error": "Task not found"}, 404
        return _snap_to_dict(snap)


__all__ = [
    "LocalProgressTracker",
    "ProgressAccessRegistry",
    "ProgressController",
    "progress_principal_key",
]
