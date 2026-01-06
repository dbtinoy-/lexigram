"""High-level throttling decorators and registries.

The ``throttle`` module sits on top of the
:mod:`~lexigram.resilience.rate_limiter` primitives and provides a
convenient decorator-first API for applying rate limits to functions and
coroutines.

**API overview**

:func:`throttle`
    Decorator — apply a rate limit to an async function::

        @throttle(calls=10, period=1.0)
        async def my_func(): ...

    Accepts ``strategy="token_bucket"`` (default) or
    ``strategy="sliding_window"``.

:class:`Throttler`
    Class-based limiter that can be applied to many functions or
    shared between components::

        throttler = Throttler(calls=5, period=1.0)

        @throttler.throttle
        async def call_a(): ...

        @throttler.throttle
        async def call_b(): ...

:class:`ThrottleRegistry`
    Singleton registry of all active :class:`Throttler` instances.
    Useful for introspection and monitoring.

:func:`get_throttle_stats`
    Retrieve call statistics for a throttled function::

        from lexigram.logging import get_logger

        logger = get_logger(__name__)
        stats = get_throttle_stats(my_func)
        logger.info("throttle_stats", allowed=stats["allowed_requests"], throttled=stats["throttled_requests"])

See :mod:`~lexigram.resilience.rate_limiter` for the underlying primitives.
"""

from __future__ import annotations

from lexigram.resilience.throttle.throttle import (
    Throttler,
    ThrottleRegistry,
    get_throttle_stats,
    throttle,
)

__all__ = ["ThrottleRegistry", "Throttler", "get_throttle_stats", "throttle"]
