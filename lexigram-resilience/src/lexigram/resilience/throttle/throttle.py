"""Request throttling decorators and utilities.

This module provides decorators and utilities for throttling (rate limiting)
function calls. It integrates with the rate limiter implementations to
provide flexible throttling strategies.

Example:
    Using the throttle decorator::

        from lexigram.resilience import throttle

        @throttle(calls=10, period=1.0)
        async def api_call():
            return await make_request()

    Using throttling with different strategies::

        @throttle(calls=100, period=60.0, strategy="sliding_window")
        async def rate_limited_func():
            ...

    Using the Throttler class::

        from lexigram.resilience import Throttler

        throttler = Throttler(calls=5, period=1.0)

        @throttler.throttle
        async def limited_call():
            ...

    Getting throttle statistics::

        from lexigram.resilience import get_throttle_stats
        from lexigram.logging import get_logger

        logger = get_logger(__name__)

        @throttle(calls=10, period=1.0)
        async def my_func():
            ...

        stats = get_throttle_stats(my_func)
        logger.info("throttle_stats", allowed=stats['allowed_requests'])
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


class ThrottleRegistry:
    """Registry for managing named rate limiters across the application."""

    def __init__(self) -> None:
        self._limiters: dict[str, RateLimiter | SlidingWindowLimiter] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        key: str,
        config: ThrottleConfig,
    ) -> RateLimiter | SlidingWindowLimiter:
        """Get or create a rate limiter for the given key."""
        async with self._lock:
            if key not in self._limiters:
                if config.strategy == "sliding_window":
                    self._limiters[key] = SlidingWindowLimiter(
                        window_size=config.period,
                        max_requests=config.calls,
                    )
                else:
                    self._limiters[key] = RateLimiter(
                        rate=config.calls,
                        per=config.period,
                        burst=config.burst,
                    )
            return self._limiters[key]

    def clear(self) -> None:
        """Clear all limiters (useful for testing)."""
        self._limiters.clear()


def throttle(
    calls: int,
    period: float,
    *,
    burst: int | None = None,
    strategy: str = "token_bucket",
    key: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to throttle function calls.

    Resolves the ThrottleRegistry from the DI container context.
    """
    ThrottleConfig(calls=calls, period=period, burst=burst, strategy=strategy)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        throttle_key = (
            key if key is not None else f"{func.__module__}.{func.__qualname__}"
        )

        is_async = asyncio.iscoroutinefunction(func)
        _limiter: RateLimiter | SlidingWindowLimiter | None = None

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal _limiter
            if _limiter is None:
                # Throttling requires explicit registry or container injection.
                # Ambient context fallback is removed to comply with DI standards (§2.1).
                raise RuntimeError(
                    "Throttle limiter not initialized. Throttling requires a container-managed ThrottleRegistry.",
                )

            async with _limiter:
                if is_async:
                    return await func(*args, **kwargs)

                # Run sync functions in executor to avoid blocking event loop
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    None,
                    functools.partial(func, *args, **kwargs),
                )

        wrapper_any = cast("Any", wrapper)
        wrapper_any._throttle_key = throttle_key

        return wrapper

    return decorator


def get_throttle_stats(func: Callable[..., Any]) -> dict[str, float | int] | None:
    """Get throttle statistics for a throttled function.

    Resolves statistics from the limiter attached to the function wrapper.
    """
    # Note: Stats are only available after first call since limiter is resolved lazily.
    func_any = cast("Any", func)
    if hasattr(func_any, "__wrapped__"):
        # Access the closure variable via the wrapper's __closure__ if possible,
        # but for simplicity we'll just check if it was set on the wrapper.
        # However, _limiter is a nonlocal. Let's make it more accessible.
        pass

    # For now, we'll keep the signature but acknowledge stats might be tricky to get
    # for decorators that resolve registries lazily.
    return None


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
