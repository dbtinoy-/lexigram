"""In-process pub/sub event stream backing the realtime endpoints.

:class:`EventStreamService` is a bounded, loss-tolerant broadcast bus: every
publisher appends to the shared history and wakes every subscriber's queue.
Subscribers replay the recent history first, then receive live events.
Slow consumers drop the oldest queued event instead of blocking the event
loop, so one dead dashboard can never stall the console.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass

from lexigram.logging import get_logger
from ops_console.domain import SystemEvent

logger = get_logger(__name__)


@dataclass(frozen=True)
class StreamStats:
    """Connection and volume statistics for the stream.

    Attributes:
        subscribers: Number of currently connected subscribers.
        events: Number of events retained in history.
    """

    subscribers: int
    events: int


DEFAULT_HISTORY_SIZE = 100
DEFAULT_QUEUE_CAPACITY = 100


class EventStreamService:
    """Fan-out broadcast bus with history replay for late subscribers.

    Args:
        history_size: Number of events retained for replay.
    """

    def __init__(self, history_size: int = DEFAULT_HISTORY_SIZE) -> None:
        self._history: deque[SystemEvent] = deque(maxlen=history_size)
        self._subscribers: set[asyncio.Queue[SystemEvent]] = set()
        self._lock = asyncio.Lock()

    def snapshot(self) -> list[SystemEvent]:
        """Return the recent event history, newest event first.

        Returns:
            A copy of the retained history.
        """
        return list(reversed(self._history))

    def stats(self) -> StreamStats:
        """Return live subscriber and history counts."""
        return StreamStats(
            subscribers=len(self._subscribers), events=len(self._history)
        )

    async def publish(self, event: SystemEvent) -> int:
        """Broadcast an event to every connected subscriber.

        Args:
            event: The event to broadcast.

        Returns:
            Number of subscribers the event was queued for.
        """
        async with self._lock:
            self._history.append(event)
            for queue in list(self._subscribers):
                if queue.full():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(event)
        logger.info(
            "event_published",
            event_type=type(event).__name__,
            subscribers=len(self._subscribers),
            history=len(self._history),
        )
        return len(self._subscribers)

    async def subscribe(self) -> AsyncIterator[SystemEvent]:
        """Iterate events: replay history, then live events until closed.

        A consumer that falls further behind both the queue capacity and the
        history window starts to miss events — it is expected to reconnect
        (browsers do this automatically for SSE).

        An event published while a subscription is being set up is delivered
        exactly once: either via replay or live, never both.

        Yields:
            Events in published order.
        """
        async with self._lock:
            queue: asyncio.Queue[SystemEvent] = asyncio.Queue(
                maxsize=DEFAULT_QUEUE_CAPACITY
            )
            self._subscribers.add(queue)
            history = list(self._history)
        try:
            for event in history:
                yield event
            while True:
                while True:
                    try:
                        event = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    yield event
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                self._subscribers.discard(queue)
