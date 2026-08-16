"""Request throttling utilities.

This module provides the :class:`Throttler` class for throttling (rate
limiting) function calls. It integrates with the rate limiter
implementations to provide flexible throttling strategies.

Example:
    Using the Throttler class::

        from lexigram.resilience import Throttler

        throttler = Throttler(calls=5, period=1.0)

        @throttler.throttle
        async def limited_call():
            ...

    Using throttling with different strategies::

        throttler = Throttler(calls=100, period=60.0, strategy="sliding_window")

        @throttler.throttle
        async def rate_limited_func():
            ...
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import functools
from typing import Any, TypeVar, cast

from lexigram.contracts.observability.metrics import MetricsRecorderProtocol
from lexigram.resilience.rate_limiter import RateLimiter, SlidingWindowLimiter
from lexigram.resilience.rate_limiter.models import RateLimiterStats

T = TypeVar("T")


@dataclass
class ThrottleConfig:
    """Configuration for throttle behavior.

    Attributes:
        calls: Maximum number of calls allowed within the period.
        period: Time period in seconds.
        burst: Maximum burst size for token bucket strategy.
        strategy: Rate limiting strategy ("token_bucket" or "sliding_window").
    """

    calls: int
    period: float
    burst: int | None = None
    strategy: str = "token_bucket"


class Throttler:
    """Class-based throttler for more control over rate limiting.

    Provides a Throttler instance that can be used to throttle multiple
    functions or to dynamically control throttling behavior.

    Example:
        Using Throttler class::

            throttler = Throttler(calls=5, period=1.0)

            @throttler.throttle
            async def limited_func():
                ...

            # Or use directly
            await throttler.acquire()
    """

    def __init__(
        self,
        calls: int,
        period: float,
        *,
        burst: int | None = None,
        strategy: str = "token_bucket",
        metrics: MetricsRecorderProtocol | None = None,
    ) -> None:
        """Initialize the throttler.

        Args:
            calls: Maximum number of calls allowed within the period.
            period: Time period in seconds.
            burst: Maximum burst size for token bucket strategy.
            strategy: Rate limiting strategy - "token_bucket" or "sliding_window".
            metrics: Optional :class:`~lexigram.contracts.observability.protocols.MetricsRecorderProtocol`
                for emitting ``throttle.allowed`` and ``throttle.denied`` counters.
                When provided, every :meth:`acquire` and :meth:`try_acquire` call
                records its outcome so telemetry dashboards can track throttle
                activity without polling :meth:`get_stats`.
        """
        self.config = ThrottleConfig(
            calls=calls,
            period=period,
            burst=burst,
            strategy=strategy,
        )
        self._metrics = metrics

        self._limiter: RateLimiter | SlidingWindowLimiter
        if strategy == "sliding_window":
            self._limiter = SlidingWindowLimiter(window_size=period, max_requests=calls)
        else:
            self._limiter = RateLimiter(rate=calls, per=period, burst=burst)

    def throttle(
        self,
        func: Callable[..., Any],
    ) -> Callable[..., Any]:
        """Decorator to throttle a function using this Throttler.

        Args:
            func: The function to throttle.

        Returns:
            The wrapped function with throttling applied.

        Example:
            >>> throttler = Throttler(calls=10, period=1.0)
            >>>
            >>> @throttler.throttle
            ... async def limited_api_call():
            ...     return await fetch_data()
        """

        is_async = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            async with self._limiter:
                if is_async:
                    return await func(*args, **kwargs)

                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    None,
                    functools.partial(func, *args, **kwargs),
                )

        wrapper_any = cast("Any", wrapper)
        wrapper_any._throttle_limiter = self._limiter
        return wrapper

    async def acquire(self) -> None:
        """Acquire permission to proceed, blocking if rate exceeded.

        Emits ``throttle.allowed`` via the :class:`~lexigram.contracts.observability.protocols.MetricsRecorderProtocol`
        when one was provided at construction time.

        Example:
            >>> throttler = Throttler(calls=10, period=1.0)
            >>> await throttler.acquire()
            >>> # Can proceed with operation
        """
        await self._limiter.acquire()
        if self._metrics is not None:
            self._metrics.increment("throttle.allowed")

    async def try_acquire(self) -> bool:
        """Try to acquire permission without blocking.

        Emits ``throttle.allowed`` or ``throttle.denied`` via the
        :class:`~lexigram.contracts.observability.protocols.MetricsRecorderProtocol` when one
        was provided at construction time.

        Returns:
            True if permission was granted, False if rate limit exceeded.

        Example:
            >>> throttler = Throttler(calls=10, period=1.0)
            >>> if await throttler.try_acquire():
            ...     # Proceed with operation
        """
        allowed = await self._limiter.try_acquire()
        if self._metrics is not None:
            if allowed:
                self._metrics.increment("throttle.allowed")
            else:
                self._metrics.increment("throttle.denied")
        return allowed

    def get_stats(self) -> dict:
        """Get throttler statistics.

        Returns:
            Dictionary with throttle statistics.

        Example:
            >>> from lexigram.logging import get_logger
            >>> logger = get_logger(__name__)
            >>> throttler = Throttler(calls=10, period=1.0)
            >>> stats = throttler.get_stats()
            >>> logger.info("stats", allowed=stats['allowed_requests'])
        """
        stats = self._limiter.get_stats()
        if isinstance(stats, RateLimiterStats):
            return {
                "total_requests": stats.total_requests,
                "allowed_requests": stats.allowed_requests,
                "denied_requests": stats.denied_requests,
                "total_wait_time": stats.total_wait_time,
            }
        return {
            "total_requests": stats.get("total_requests", 0),
            "allowed_requests": stats.get("allowed_requests", 0),
            "denied_requests": stats.get("denied_requests", 0),
            "total_wait_time": stats.get("total_wait_time", 0.0),
        }
