"""Real-time data subscriptions for Lexigram Admin."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lexigram.admin.data.query import QuerySpec as Query


@dataclass
class DataChange:
    """Represents a single data change event.

    Attributes:
        type: The type of change ("created", "updated", "deleted").
        resource: The name of the resource that changed.
        id: The unique identifier of the affected entity.
        data: The new data (for created/updated) or None.
        timestamp: When the change occurred.
    """

    type: Literal["created", "updated", "deleted"]
    resource: str
    id: Any
    data: dict[str, Any] | None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class DataSubscription:
    """Subscription to real-time data changes.

    This class manages the lifecycle of a data subscription, typically
    backed by Server-Sent Events (SSE) or a message broker.
    """

    def __init__(
        self,
        resource: str,
        query: Query | None = None,
        *,
        buffer_size: int = 100,
    ) -> None:
        """Initialize a subscription.

        Args:
            resource: The resource name to watch.
            query: Optional query to filter which changes to receive.
            buffer_size: Maximum number of events to buffer in the queue.
        """
        self.resource = resource
        self.query = query
        self._queue: asyncio.Queue[DataChange] = asyncio.Queue(maxsize=buffer_size)
        self._active = False

    async def subscribe(self) -> AsyncIterator[DataChange]:
        """Start receiving data change events.

        Yields:
            DataChange objects as they occur.
        """
        self._active = True
        try:
            while self._active:
                change = await self._queue.get()
                yield change
        finally:
            self._active = False

    async def unsubscribe(self) -> None:
        """Stop the subscription and clear the queue."""
        self._active = False
        # Clear the queue by pulling all items
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def emit(self, change: DataChange) -> None:
        """Manually emit a change into this subscription (infrastructure use)."""
        if not self._active:
            return

        # If the subscription has a query, we should ideally check if the
        # changed data matches the query. This is complex for general queries.
        # For now, we just check resource name.
        if change.resource != self.resource:
            return

        try:
            # We don't want to block if the queue is full,
            # we'd rather drop old events if necessary or let the user handle it.
            if self._queue.full():
                self._queue.get_nowait()  # Drop oldest
            self._queue.put_nowait(change)
        except (asyncio.QueueFull, asyncio.QueueEmpty):
            pass
