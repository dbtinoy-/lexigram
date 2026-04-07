from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import dataclasses
import types
from typing import Any, Self

from lexigram.primitives import clock as ambient_clock
from lexigram.resilience.rate_limiter.models import RateLimiterStats


class TokenBucket:
    """Async token bucket rate limiter.

    Implements the token-bucket algorithm: tokens are added at a fixed
    *refill_rate* (tokens per second) up to *capacity*, and each
    :meth:`acquire` call consumes one or more tokens.

    Args:
        capacity: Maximum number of tokens the bucket can hold.
        refill_rate: Tokens added per second.
        initial_tokens: Starting token count (defaults to *capacity*).
    """

    def __init__(
        self,
        capacity: float,
        refill_rate: float,
        initial_tokens: float | None = None,
    ) -> None:
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._tokens: float = float(
            initial_tokens if initial_tokens is not None else capacity
        )
        self._last_refill = ambient_clock.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        """Add tokens proportional to elapsed time since last refill."""
        now = ambient_clock.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    async def acquire(self, tokens: int = 1) -> None:
        """Block until *tokens* are available in the bucket.

        Args:
            tokens: Number of tokens to consume (default 1).

        Raises:
            ValueError: If *tokens* exceeds :attr:`capacity`.
        """
        if tokens > self.capacity:
            msg = "Cannot acquire more tokens than bucket capacity"
            raise ValueError(msg)

        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                wait_time = (tokens - self._tokens) / self.refill_rate
            await asyncio.sleep(wait_time)

    async def try_acquire(self, tokens: int = 1) -> bool:
        """Non-blocking token acquisition.

        Args:
            tokens: Number of tokens to consume (default 1).

        Returns:
            ``True`` if the tokens were acquired; ``False`` if insufficient.
        """
        async with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens (snapshot, not thread-safe)."""
        return self._tokens


class RateLimiter:
    """Rate limiter using token bucket algorithm."""

    def __init__(self, rate: int, per: float = 1.0, burst: int | None = None) -> None:
        self.rate = rate
        self.per = per
        self.burst = burst if burst is not None else rate
        refill_rate = rate / per
        self._bucket = TokenBucket(capacity=self.burst, refill_rate=refill_rate)
        self._stats = RateLimiterStats()

    async def acquire(self) -> None:
        """Acquire permission to proceed, blocking if rate exceeded."""
        start = ambient_clock.monotonic()
        await self._bucket.acquire()
        wait_time = ambient_clock.monotonic() - start

        async with self._bucket._lock:
            self._stats.total_requests += 1
            self._stats.allowed_requests += 1
            self._stats.total_wait_time += wait_time

    async def try_acquire(self) -> bool:
        """Try to acquire permission without blocking."""
        acquired = await self._bucket.try_acquire()

        async with self._bucket._lock:
            self._stats.total_requests += 1
            if acquired:
                self._stats.allowed_requests += 1
            else:
                self._stats.denied_requests += 1

        return acquired

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[None]:
        """Use rate limiter as a callable context manager."""
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

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics as a plain mapping.

        Returns:
            Dictionary with counters: total_requests, allowed_requests,
            denied_requests, total_wait_time.
        """
        return dataclasses.asdict(self._stats)


__all__ = ["RateLimiter", "TokenBucket"]
