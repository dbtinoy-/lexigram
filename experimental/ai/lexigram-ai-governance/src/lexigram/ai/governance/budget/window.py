"""Sliding-window counter for rate / budget enforcement."""

from __future__ import annotations

import asyncio
from collections import deque
import time


class SlidingWindowCounter:
    """Thread-safe sliding window counter for rate / budget enforcement.

    Uses a deque of ``(timestamp, value)`` tuples.  On each access,
    entries older than *window_seconds* are dropped.  Reservation
    amounts (``reserve``/``release_reservation``) are held separately
    from used entries and counted by ``total()`` so concurrent
    reservations cannot oversubscribe a limit.
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._window = window_seconds
        self._entries: deque[tuple[float, float]] = deque()
        self._reserved: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def add(self, value: float) -> float:
        """Record *value* and return the updated used-window total.

        Args:
            value: Value to add (token count, cost in USD, etc.).

        Returns:
            Sum of used values in the current window after adding *value*.
        """
        now = time.monotonic()
        async with self._lock:
            self._entries.append((now, value))
            self._prune(now)
            return sum(v for _, v in self._entries)

    async def total(self) -> float:
        """Return the window total including reservations."""
        now = time.monotonic()
        async with self._lock:
            self._prune(now)
            used = sum(v for _, v in self._entries)
            return used + sum(self._reserved.values())

    async def reserve(self, reservation_id: str, value: float) -> None:
        """Reserve *value* under *reservation_id* against the limit.

        Args:
            reservation_id: Identifier used to release the reservation.
            value: Amount to hold (token count, cost in USD, etc.).
        """
        async with self._lock:
            self._reserved[reservation_id] = (
                self._reserved.get(reservation_id, 0.0) + value
            )

    async def release_reservation(self, reservation_id: str) -> None:
        """Release a reservation; harmless when unknown."""
        async with self._lock:
            self._reserved.pop(reservation_id, None)

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        while self._entries and self._entries[0][0] < cutoff:
            self._entries.popleft()


__all__ = ["SlidingWindowCounter"]
