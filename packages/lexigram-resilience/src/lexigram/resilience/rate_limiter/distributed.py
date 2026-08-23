"""Distributed sliding-window rate limiter backed by a StateStoreProtocol.

Uses :class:`~lexigram.contracts.infra.protocols.StateStoreProtocol` so that the
limit is shared across all process replicas.  Timestamps are persisted as
a JSON-serialised list; the TTL is set to the window ``period`` so the key
expires automatically between bursts.

.. note::
    This implementation is eventually-consistent under heavy concurrent
    load.  For strict atomic enforcement, back the ``StateStoreProtocol`` with a
    Redis implementation that supports atomic compare-and-swap semantics.

Example::

    from lexigram.resilience.rate_limiter import DistributedRateLimiter

    limiter = DistributedRateLimiter(
        name="payments-api",
        max_calls=100,
        period=60.0,
        store=redis_state_store,
    )

    if await limiter.try_acquire():
        await call_external_api()
    else:
        raise TooManyRequestsError("Rate limit exceeded")
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.serialization import dumps_str, loads_str

if TYPE_CHECKING:
    from lexigram.contracts.infra.state import StateStoreProtocol

logger = get_logger(__name__)

_KEY_PREFIX = "lexigram:resilience:ratelimit"


class DistributedRateLimiter:
    """Sliding-window rate limiter that persists state in a :class:`StateStoreProtocol`.

    The window is defined by the *most recent* ``period`` seconds.  Each
    successful acquisition records a timestamp; stale entries (older than
    ``period``) are discarded on every read so the effective count always
    reflects only the live window.

    Args:
        name: Logical name for this limiter; used as part of the cache key.
        max_calls: Maximum number of acquisitions permitted within ``period``.
        period: Window size in seconds (float).
        store: A :class:`~lexigram.contracts.infra.protocols.StateStoreProtocol`
            implementation used to persist window timestamps across replicas.
    """

    def __init__(
        self,
        name: str,
        max_calls: int,
        period: float,
        store: StateStoreProtocol,
    ) -> None:
        if max_calls <= 0:
            msg = "max_calls must be a positive integer"
            raise ValueError(msg)
        if period <= 0:
            msg = "period must be a positive number"
            raise ValueError(msg)

        self._name = name
        self._max_calls = max_calls
        self._period = period
        self._store = store
        self._key = f"{_KEY_PREFIX}:{name}"

        # In-process stats (approximate — not distributed)
        self._total_requests: int = 0
        self._allowed_requests: int = 0
        self._denied_requests: int = 0

        logger.debug(
            "distributed_rate_limiter_created",
            name=name,
            max_calls=max_calls,
            period=period,
            key=self._key,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_timestamps(self) -> list[float]:
        """Load the current timestamp list from the store."""
        raw = await self._store.get(self._key)
        if raw is None:
            return []
        try:
            data = loads_str(raw) if isinstance(raw, (str, bytes)) else raw  # type: ignore[arg-type]
            if isinstance(data, list):
                return [float(t) for t in data]
        except (ValueError, TypeError) as exc:
            logger.warning(
                "distributed_rate_limiter_corrupt_state",
                name=self._name,
                error=str(exc),
            )
        return []

    async def _save_timestamps(self, timestamps: list[float]) -> None:
        """Persist the timestamp list back to the store with a rolling TTL."""
        ttl = max(1, int(self._period) + 1)
        await self._store.set(self._key, dumps_str(timestamps), ttl=ttl)

    def _prune(self, timestamps: list[float], now: float) -> list[float]:
        """Remove timestamps that have fallen outside the current window."""
        cutoff = now - self._period
        return [t for t in timestamps if t >= cutoff]

    # ------------------------------------------------------------------
    # Public API (RateLimiterProtocol)
    # ------------------------------------------------------------------

    async def try_acquire(self) -> bool:
        """Attempt to consume one token without blocking.

        Returns:
            ``True`` if the acquisition succeeded (count was under the limit);
            ``False`` if the limit is currently exhausted.
        """
        self._total_requests += 1
        now = ambient_clock.timestamp()

        timestamps = await self._load_timestamps()
        active = self._prune(timestamps, now)

        if len(active) < self._max_calls:
            active.append(now)
            await self._save_timestamps(active)
            self._allowed_requests += 1
            logger.debug(
                "distributed_rate_limiter_acquired",
                name=self._name,
                window_count=len(active),
                max_calls=self._max_calls,
            )
            return True

        self._denied_requests += 1
        logger.debug(
            "distributed_rate_limiter_denied",
            name=self._name,
            window_count=len(active),
            max_calls=self._max_calls,
        )
        return False

    async def acquire(self) -> None:
        """Block until one token is available and consume it.

        Polls :meth:`try_acquire` using an exponential back-off that is
        capped at half the window ``period`` so callers do not spin
        excessively during sustained overload.
        """
        delay = 0.05  # start at 50 ms
        max_delay = max(0.05, self._period / 2)

        while not await self.try_acquire():
            # Subtract one denied count added by try_acquire so that
            # blocking acquire() counts as a single request overall.
            self._denied_requests -= 1
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)

    def get_stats(self) -> dict[str, Any]:
        """Return current in-process limiter statistics.

        Returns:
            A plain mapping with keys ``total_requests``, ``allowed_requests``,
            ``denied_requests``, ``name``, ``max_calls``, and ``period``.

        .. note::
            Statistics are local to the current process replica and are not
            aggregated across the distributed fleet.
        """
        return {
            "name": self._name,
            "max_calls": self._max_calls,
            "period": self._period,
            "total_requests": self._total_requests,
            "allowed_requests": self._allowed_requests,
            "denied_requests": self._denied_requests,
        }


__all__ = ["DistributedRateLimiter"]
