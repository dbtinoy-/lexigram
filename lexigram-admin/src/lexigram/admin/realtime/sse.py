"""Server-Sent Events (SSE) integration for lexigram-admin.

This module provides SSE handlers for real-time updates in admin.

FWK-10: SSE for real-time updates using @sse_endpoint.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from lexigram.contracts.web.sse import ServerSentEvent, SseResponseFactoryProtocol

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# ============================================================================
# Protocols for optional web integration
# ============================================================================

# Placeholder types for when lexigram-web is not available
# These are replaced via container registration when lexigram-web is present


class SSEHandler:
    """Base SSE handler class.

    This is a local implementation that does not depend on lexigram-web.
    When lexigram-web is available, its SSEHandler is registered in the container
    and resolved through IoC.
    """

    async def stream(self) -> AsyncGenerator[dict[str, Any], None]:
        """Yield SSE events as dictionaries."""
        if False:  # pragma: no cover
            yield {}
        return


# ============================================================================
# Event Types
# ============================================================================


class AdminEventType(StrEnum):
    """Standard admin event types."""

    # Resource events
    RESOURCE_CREATED = "resource.created"
    RESOURCE_UPDATED = "resource.updated"
    RESOURCE_DELETED = "resource.deleted"

    # Bulk operation events
    BULK_PROGRESS = "bulk.progress"
    BULK_COMPLETED = "bulk.completed"
    BULK_FAILED = "bulk.failed"

    # Notification events
    NOTIFICATION = "notification"
    TOAST = "toast"

    # System events
    HEARTBEAT = "heartbeat"
    RECONNECT = "reconnect"


@dataclass
class AdminEvent:
    """Admin SSE event."""

    event_type: AdminEventType | str
    data: dict[str, Any]
    id: str | None = None
    resource_type: str | None = None
    resource_id: Any = None
    tenant_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for SSE."""
        return {
            "event": str(
                self.event_type.value
                if isinstance(self.event_type, AdminEventType)
                else self.event_type,
            ),
            "data": {
                **self.data,
                "timestamp": self.timestamp.isoformat(),
                "resource_type": self.resource_type,
                "resource_id": self.resource_id,
            },
            "id": self.id,
        }


# ============================================================================
# Event Hub
# ============================================================================


class AdminEventHub:
    """Central hub for admin SSE events.

    Manages subscriptions and broadcasts events to connected clients.

    Example:
        >>> hub = AdminEventHub()
        >>>
        >>> # Subscribe to events
        >>> async for event in hub.subscribe(user_id=1, resources=["users"]):
        ...     print(event)
        >>>
        >>> # Publish an event
        >>> await hub.publish(AdminEvent(
        ...     event_type=AdminEventType.RESOURCE_UPDATED,
        ...     data={"changes": {...}},
        ...     resource_type="users",
        ...     resource_id=42,
        ... ))
    """

    def __init__(self) -> None:
        """Initialize the hub."""
        self._subscribers: dict[str, asyncio.Queue[AdminEvent]] = {}
        self._resource_subscriptions: dict[
            str,
            set[str],
        ] = {}  # resource -> subscriber_ids
        self._user_subscriptions: dict[Any, set[str]] = {}  # user_id -> subscriber_ids

    def _generate_subscriber_id(self, user_id: Any | None = None) -> str:
        """Generate unique subscriber ID."""
        import uuid

        base = str(uuid.uuid4())[:8]
        if user_id:
            return f"{user_id}:{base}"
        return base

    async def subscribe(
        self,
        user_id: Any | None = None,
        resources: list[str] | None = None,
        event_types: list[AdminEventType] | None = None,
    ) -> AsyncGenerator[AdminEvent, None]:
        """Subscribe to admin events.

        Args:
            user_id: Optional user ID for user-specific events
            resources: Optional list of resource types to watch
            event_types: Optional list of event types to receive

        Yields:
            AdminEvent objects as they arrive
        """
        subscriber_id = self._generate_subscriber_id(user_id)
        queue: asyncio.Queue[AdminEvent] = asyncio.Queue()

        # Register subscriber
        self._subscribers[subscriber_id] = queue

        if resources:
            for resource in resources:
                if resource not in self._resource_subscriptions:
                    self._resource_subscriptions[resource] = set()
                self._resource_subscriptions[resource].add(subscriber_id)

        if user_id:
            if user_id not in self._user_subscriptions:
                self._user_subscriptions[user_id] = set()
            self._user_subscriptions[user_id].add(subscriber_id)

        try:
            while True:
                event = await queue.get()

                # Filter by event type if specified
                if event_types and event.event_type not in event_types:
                    continue

                yield event
        finally:
            # Cleanup on disconnect
            self._subscribers.pop(subscriber_id, None)

            if resources:
                for resource in resources:
                    if resource in self._resource_subscriptions:
                        self._resource_subscriptions[resource].discard(subscriber_id)

            if user_id and user_id in self._user_subscriptions:
                self._user_subscriptions[user_id].discard(subscriber_id)

    async def publish(
        self,
        event: AdminEvent,
        target_users: list[Any] | None = None,
    ) -> int:
        """Publish an event to subscribers.

        Args:
            event: Event to publish
            target_users: Optional specific users to target

        Returns:
            Number of subscribers that received the event
        """
        delivered = 0
        target_subscriber_ids: set[str] = set()

        # Determine target subscribers
        if target_users:
            for user_id in target_users:
                if user_id in self._user_subscriptions:
                    target_subscriber_ids.update(self._user_subscriptions[user_id])
        elif event.resource_type:
            # Broadcast to resource subscribers
            if event.resource_type in self._resource_subscriptions:
                target_subscriber_ids.update(
                    self._resource_subscriptions[event.resource_type],
                )
        else:
            # Broadcast to all
            target_subscriber_ids.update(self._subscribers.keys())

        # Deliver event
        for subscriber_id in target_subscriber_ids:
            if subscriber_id in self._subscribers:
                try:
                    self._subscribers[subscriber_id].put_nowait(event)
                    delivered += 1
                except asyncio.QueueFull:
                    pass  # Skip if queue is full

        return delivered

    async def publish_resource_event(
        self,
        event_type: AdminEventType,
        resource_type: str,
        resource_id: Any,
        data: dict[str, Any] | None = None,
    ) -> int:
        """Convenience method to publish a resource event."""
        event = AdminEvent(
            event_type=event_type,
            data=data or {},
            resource_type=resource_type,
            resource_id=resource_id,
        )
        return await self.publish(event)

    async def publish_notification(
        self,
        title: str,
        message: str,
        level: str = "info",
        target_users: list[Any] | None = None,
    ) -> int:
        """Publish a notification event."""
        event = AdminEvent(
            event_type=AdminEventType.NOTIFICATION,
            data={
                "title": title,
                "message": message,
                "level": level,
            },
        )
        return await self.publish(event, target_users=target_users)

    async def publish_toast(
        self,
        message: str,
        variant: str = "success",
        duration: int = 5000,
        target_users: list[Any] | None = None,
    ) -> int:
        """Publish a toast notification event."""
        event = AdminEvent(
            event_type=AdminEventType.TOAST,
            data={
                "message": message,
                "variant": variant,
                "duration": duration,
            },
        )
        return await self.publish(event, target_users=target_users)


HAS_SSE = True  # local placeholder is always available

# ============================================================================
# Admin SSE Handler
# ============================================================================


class AdminEventsHandler(SSEHandler if HAS_SSE else object):  # type: ignore[misc]
    """SSE handler for admin events.

    Streams events from AdminEventHub to connected clients.

    Usage with lexigram.web:
        >>> @sse_endpoint("/admin/events")
        ... class AdminEventsEndpoint(AdminEventsHandler):
        ...     pass
    """

    heartbeat_interval: int = 30
    retry: int = 3000
    event_types: list[str] = [e.value for e in AdminEventType]

    def __init__(self, hub: AdminEventHub) -> None:
        self._hub = hub

    async def stream(self, request: Any) -> AsyncGenerator[dict[str, Any], None]:
        """Stream admin events to client."""
        # Get user from request
        user = getattr(request, "user", None)
        user_id = getattr(user, "id", None) if user else None

        # Get resource filter from query params
        resources = None
        if hasattr(request, "query_params"):
            resources_param = request.query_params.get("resources")
            if resources_param:
                resources = resources_param.split(",")

        # Subscribe and yield events
        async for event in self._hub.subscribe(
            user_id=user_id,
            resources=resources,
        ):
            yield event.to_dict()

    async def on_connect(self, request: Any) -> None:
        """Handle client connection."""
        # Could log connection or update presence

    async def on_disconnect(self, request: Any) -> None:
        """Handle client disconnection."""
        # Could log disconnection or update presence


# ============================================================================
# Bulk Operation Progress Handler
# ============================================================================


class BulkOperationProgressHandler(SSEHandler if HAS_SSE else object):  # type: ignore[misc]
    """SSE handler for bulk operation progress.

    Streams progress updates for long-running bulk operations.

    Usage:
        >>> @sse_endpoint("/admin/bulk/{operation_id}/progress")
        ... class BulkProgressEndpoint(BulkOperationProgressHandler):
        ...     pass
    """

    heartbeat_interval: int = 5
    retry: int = 1000

    # In-memory progress tracking (should be Redis-backed in production)
    _progress: dict[str, dict[str, Any]] = {}

    @classmethod
    def start_operation(
        cls,
        operation_id: str,
        total: int,
        description: str = "",
    ) -> None:
        """Start tracking a new operation."""
        cls._progress[operation_id] = {
            "total": total,
            "processed": 0,
            "failed": 0,
            "description": description,
            "status": "running",
            "started_at": datetime.now(UTC).isoformat(),
        }

    @classmethod
    def update_progress(
        cls,
        operation_id: str,
        processed: int,
        failed: int = 0,
    ) -> None:
        """Update operation progress."""
        if operation_id in cls._progress:
            cls._progress[operation_id]["processed"] = processed
            cls._progress[operation_id]["failed"] = failed

    @classmethod
    def complete_operation(
        cls,
        operation_id: str,
        success: bool = True,
        message: str = "",
    ) -> None:
        """Mark operation as complete."""
        if operation_id in cls._progress:
            cls._progress[operation_id]["status"] = "completed" if success else "failed"
            cls._progress[operation_id]["message"] = message
            cls._progress[operation_id]["completed_at"] = datetime.now(
                UTC,
            ).isoformat()

    async def stream(self, request: Any) -> AsyncGenerator[dict[str, Any], None]:
        """Stream progress for an operation."""
        operation_id = ""
        if hasattr(request, "path_params"):
            operation_id = request.path_params.get("operation_id", "")

        if not operation_id or operation_id not in self._progress:
            yield {
                "event": "error",
                "data": {"message": "Operation not found"},
            }
            return

        while True:
            progress = self._progress.get(operation_id)
            if not progress:
                break

            yield {
                "event": "progress",
                "data": progress,
            }

            if progress["status"] in ("completed", "failed"):
                # Final event
                yield {
                    "event": progress["status"],
                    "data": progress,
                }
                # Cleanup
                self._progress.pop(operation_id, None)
                break

            await asyncio.sleep(0.5)


# ============================================================================
# SSE Response Helpers
# ============================================================================


def create_sse_response(
    event_generator: AsyncGenerator[dict[str, Any], None],
    sse_factory: SseResponseFactoryProtocol,
) -> Any:
    """Create an SSE response from an event generator via an injected factory.

    The ``sse_factory`` is registered in the DI container by ``lexigram-web``
    during ``WebProvider.boot()``.  Callers must resolve
    ``SseResponseFactoryProtocol`` from the container and pass it here.

    Args:
        event_generator: Async generator yielding event-data dicts.  Each dict
            may contain ``data``, ``event``, ``id``, and ``retry`` keys.
        sse_factory: Factory that wraps a ``ServerSentEvent`` generator into a
            framework streaming response.

    Returns:
        A framework-specific SSE streaming HTTP response.
    """

    async def wrapped_generator() -> AsyncGenerator[ServerSentEvent, None]:
        async for event_data in event_generator:
            yield ServerSentEvent(
                data=event_data.get("data", event_data),
                event=event_data.get("event"),
                event_id=event_data.get("id"),
                retry=event_data.get("retry"),
            )

    return sse_factory.create_response(wrapped_generator())


__all__ = [
    # Flags
    "HAS_SSE",
    "AdminEvent",
    # Hub
    "AdminEventHub",
    # Event types
    "AdminEventType",
    # Handlers
    "AdminEventsHandler",
    "BulkOperationProgressHandler",
    # Helpers
    "create_sse_response",
]
