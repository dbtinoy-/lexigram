"""Rate-limiting primitives — token-bucket and sliding-window algorithms.

**Choosing between rate_limiter and throttle**

Lexigram's rate-control API is layered:

.. code-block:: text

    throttle/                   ← High-level API (prefer this)
    │  Throttler class          — Reusable per-function limiter
    │
    └── rate_limiter/           ← Low-level primitives (used internally)
           RateLimiter          — Token-bucket limiter with acquire()/try_acquire()
           TokenBucket          — Raw token-bucket algorithm
           SlidingWindowLimiter — Sliding-window (fixed interval) limiter

When to use each layer:

* **``Throttler``** (recommended): decorating a specific async function,
  endpoint handler, or task so that it may only run at a controlled rate.
  The ``Throttler(calls=N, period=T)`` + ``@throttler.throttle`` pattern
  covers the majority of use cases.

* **``rate_limiter`` primitives**: when you need fine-grained programmatic
  control — for example, sharing one :class:`RateLimiter` across multiple
  code paths, adjusting limits at runtime, or querying available tokens
  before deciding to proceed.

Example — using the high-level Throttler::

    from lexigram.resilience import Throttler

    throttler = Throttler(calls=100, period=60.0)

    @throttler.throttle
    async def call_external_api() -> dict:
        ...

Example — using a shared RateLimiter::

    from lexigram.resilience.rate_limiter import RateLimiter

    _limiter = RateLimiter(rate=10, per=1.0)  # 10 req/s

    async def guarded_send(message: str) -> None:
        await _limiter.acquire()
        await _send(message)
"""

from __future__ import annotations

from lexigram.resilience.rate_limiter.distributed import DistributedRateLimiter
from lexigram.resilience.rate_limiter.models import RateLimiterStats
from lexigram.resilience.rate_limiter.sliding_window import SlidingWindowLimiter
from lexigram.resilience.rate_limiter.token_bucket import RateLimiter, TokenBucket

__all__ = [
    "DistributedRateLimiter",
    "RateLimiter",
    "RateLimiterStats",
    "SlidingWindowLimiter",
    "TokenBucket",
]
