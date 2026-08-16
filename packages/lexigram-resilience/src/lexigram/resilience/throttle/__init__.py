"""High-level throttling API.

The ``throttle`` module provides the :class:`Throttler` class — a
DI-friendly, class-based rate limiter that can be applied to many functions
or shared between components.

**API overview**

:class:`Throttler`
    Class-based limiter that can be applied to many functions or shared
    between components::

        throttler = Throttler(calls=5, period=1.0)

        @throttler.throttle
        async def call_a(): ...

        @throttler.throttle
        async def call_b(): ...

    Accepts ``strategy="token_bucket"`` (default) or
    ``strategy="sliding_window"``.

See :mod:`~lexigram.resilience.rate_limiter` for the underlying primitives.
"""

from __future__ import annotations

from lexigram.resilience.throttle.throttle import Throttler

__all__ = ["Throttler"]
