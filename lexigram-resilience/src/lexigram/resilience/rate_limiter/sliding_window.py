from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import types
from typing import Self

from lexigram.primitives import clock as ambient_clock
from lexigram.resilience.rate_limiter.models import RateLimiterStats


class SlidingWindowLimiter:
    """Sliding window rate limiter for precise request tracking."""

    def __init__(self, window_size: float, max_requests: int) -> None:
        self.window_size = window_size
        self.max_requests = max_requests
        self._requests: deque[float] = deque()
        self._lock = asyncio.Lock()
        self._stats = RateLimiterStats()

    def _cleanup_old_requests(self) -> None:
        """Remove requests outside the current window."""
        now = ambient_clock.monotonic()
        cutoff = now - self.window_size

        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

    async def acquire(self) -> None:
        """Acquire permission to proceed, blocking if window is full."""
        start = ambient_clock.monotonic()
        while True:
            async with self._lock:
                self._cleanup_old_requests()

                if len(self._requests) < self.max_requests:
                    self._requests.append(ambient_clock.monotonic())
                    wait_time_total = ambient_clock.monotonic() - start

                    self._stats.total_requests += 1
                    self._stats.allowed_requests += 1
                    self._stats.total_wait_time += wait_time_total
                    return

                oldest = self._requests[0]
                wait_time = (oldest + self.window_size) - ambient_clock.monotonic()

            if wait_time > 0:
                await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(0)

    async def try_acquire(self) -> bool:
        """Try to acquire permission without blocking."""
        async with self._lock:
            self._cleanup_old_requests()

            self._stats.total_requests += 1

            if len(self._requests) < self.max_requests:
                self._requests.append(ambient_clock.monotonic())
                self._stats.allowed_requests += 1
                return True

            self._stats.denied_requests += 1
            return False

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[None]:
        """Use limiter as a callable context manager."""
        await self.acquire()
        yield

    async def __aenter__(self) -> Self:
        """Enter the async context manager."""
        await self.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool:
        """Exit the async context manager."""
        return False

    def get_stats(self) -> RateLimiterStats:
        """Get rate limiter statistics."""
        return self._stats

    @property
    def current_requests(self) -> int:
        """Get current number of requests in the window."""
        return len(self._requests)
