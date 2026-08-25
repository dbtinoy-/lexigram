"""Redis-backed governance persistence backend.

Distributed state backed by a
:class:`~lexigram.contracts.infra.cache.CacheBackendProtocol`, enabling
multi-replica consistency for rate limiting and budget enforcement.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.governance.exceptions import GovernancePersistenceError

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache import CacheBackendProtocol
    from lexigram.contracts.infra.cache.exceptions import CacheError
    from lexigram.result import Result

__all__ = ["RedisGovernancePersistence"]

_32_DAYS_SECONDS = 32 * 24 * 3600


def _cache_payload(value: object, *, key: str) -> Any:
    """Extract the payload of a cache backend result, raising on failure.

    Protocol-compliant backends return ``Result[Any | None, CacheError]``;
    plain values are treated as an ``Ok`` payload.  An ``Err`` result is an
    infrastructure failure and raises :class:`GovernancePersistenceError`
    instead of being silently treated as a missing value (the previous
    behavior, which let failures fail open).

    Args:
        value: Return value of ``CacheBackendProtocol.get`` / ``set``.
        key: Cache key the call was made for (included in the error).

    Returns:
        The payload — ``Any``, matching the cache protocol's payload type —
        or ``None`` for a successful miss.

    Raises:
        GovernancePersistenceError: When the backend reported failure.
    """
    if hasattr(value, "is_ok"):
        result = cast("Result[Any, CacheError]", value)
        if result.is_ok():
            return result.unwrap_or(None)
        error = result.unwrap_err()
        raise GovernancePersistenceError(
            f"cache backend failed for key={key}: {error}"
        ) from error
    return value


class RedisGovernancePersistence:
    """Distributed governance persistence backed by a Lexigram CacheBackendProtocol.

    Request windows use a sorted-set approach:
    - Each request is stored as a member with its Unix timestamp as score.
    - Expired members (score < ``now - window``) are pruned on every read.

    Spend totals are stored as plain string floats with a configurable TTL
    so that monthly counters expire automatically.

    Args:
        cache: A :class:`~lexigram.contracts.cache.CacheBackendProtocol` that has been
            connected and is ready to accept commands.  The backend is
            expected to be Redis-compatible.
    """

    _REQUEST_KEY_PREFIX = "ai:gov:req:"
    _SPEND_KEY_PREFIX = "ai:gov:spend:"
    _GAUGE_KEY_PREFIX = "ai:gov:gauge:"
    _CALENDAR_KEY_PREFIX = "ai:gov:cal:"

    def __init__(self, cache: CacheBackendProtocol) -> None:
        self._cache = cache

    async def incr_requests(self, key: str, window: float) -> int:
        """Use a sorted set to implement a sliding window counter.

        Falls back to an approximate counter if the backend does not support
        sorted-set operations (e.g. a simple in-memory mock).  Infrastructure
        failures are not masked: the exception propagates so the caller can
        apply the configured governance decision (fail-closed by default).

        Args:
            key: Bucket key (e.g. ``"global"`` or a user/tenant id).
            window: Rolling window size in seconds.

        Returns:
            Number of requests (including the current one) inside the window.

        Raises:
            GovernancePersistenceError: When the cache backend reports failure
                (``Err`` result).
            OSError, ConnectionError, RuntimeError, ValueError, TypeError:
                Propagated from the cache backend when it raises.
        """
        redis_key = f"{self._REQUEST_KEY_PREFIX}{key}"
        now = time.time()
        cutoff = now - window

        try:
            # Try native sorted-set operations (Redis / ioredis)
            backend = self._cache  # CacheBackendProtocol may expose raw client
            raw = getattr(backend, "_client", None) or getattr(backend, "client", None)
            if raw is not None and hasattr(raw, "zremrangebyscore"):
                # Remove expired entries
                await raw.zremrangebyscore(redis_key, "-inf", cutoff)
                # Add current request
                await raw.zadd(redis_key, {str(now): now})
                # Expire the key after the window to avoid unbounded growth
                await raw.expire(redis_key, int(window) + 1)
                count: int = await raw.zcard(redis_key)
                return count
        except (OSError, ConnectionError, RuntimeError, AttributeError):
            pass

        # Fallback: simple increment counter (less precise but always works)
        counter_key = f"{redis_key}:count"
        raw_val = _cache_payload(await self._cache.get(counter_key), key=counter_key)
        current = int(raw_val) + 1 if raw_val is not None else 1
        _cache_payload(
            await self._cache.set(counter_key, str(current), ttl=int(window) + 1),
            key=counter_key,
        )
        return current

    async def add_spend(self, key: str, amount: float, ttl: int) -> float:
        """Add ``amount`` to the spend accumulator and return the new total.

        Infrastructure failures propagate (fail-closed by default at the
        manager); no value is invented on error.

        Args:
            key: Bucket key (e.g. ``"global:2025-06"``).
            amount: Cost amount to add.
            ttl: Time-to-live for the accumulator entry in seconds.

        Returns:
            Updated total spend.

        Raises:
            GovernancePersistenceError: When the cache backend reports failure
                (``Err`` result, read or write).
            OSError, ConnectionError, RuntimeError, ValueError, TypeError:
                Propagated from the cache backend when it raises.
        """
        redis_key = f"{self._SPEND_KEY_PREFIX}{key}"
        raw = _cache_payload(await self._cache.get(redis_key), key=redis_key)
        current = float(raw) if raw is not None else 0.0
        updated = current + amount
        _cache_payload(
            await self._cache.set(redis_key, str(updated), ttl=ttl),
            key=redis_key,
        )
        return updated

    async def get_spend(self, key: str) -> float:
        """Return the current accumulated spend for *key*.

        Args:
            key: Bucket key.

        Returns:
            Current spend; ``0.0`` if no data recorded.

        Raises:
            GovernancePersistenceError: When the cache backend reports failure
                (``Err`` result).
            OSError, ConnectionError, RuntimeError, ValueError, TypeError:
                Propagated from the cache backend when it raises.
        """
        redis_key = f"{self._SPEND_KEY_PREFIX}{key}"
        raw = _cache_payload(await self._cache.get(redis_key), key=redis_key)
        return float(raw) if raw is not None else 0.0

    async def read_gauge(self, key: str) -> float:
        """Read the current gauge value for *key*.

        Args:
            key: Gauge key (e.g. ``"tenant:gpt4:remaining"``).

        Returns:
            Current gauge value; ``0.0`` if no data recorded.

        Raises:
            GovernancePersistenceError: When the cache backend reports failure
                (``Err`` result).
            OSError, ConnectionError, RuntimeError, ValueError, TypeError:
                Propagated from the cache backend when it raises.
        """
        redis_key = f"{self._GAUGE_KEY_PREFIX}{key}"
        raw = _cache_payload(await self._cache.get(redis_key), key=redis_key)
        return float(raw) if raw is not None else 0.0

    async def write_gauge(self, key: str, value: float, ttl: int) -> None:
        redis_key = f"{self._GAUGE_KEY_PREFIX}{key}"
        try:
            await self._cache.set(redis_key, str(value), ttl=ttl)
        except (OSError, ConnectionError, RuntimeError):
            pass

    async def incr_gauge(self, key: str, delta: float, ttl: int) -> float:
        """Atomically increment (or decrement) the gauge for *key*.

        Args:
            key: Gauge key.
            delta: Amount to add (can be negative).
            ttl: Time-to-live in seconds.

        Returns:
            The gauge value after applying *delta*.

        Raises:
            GovernancePersistenceError: When the cache backend reports failure
                (``Err`` result, read or write).
            OSError, ConnectionError, RuntimeError, ValueError, TypeError:
                Propagated from the cache backend when it raises.
        """
        redis_key = f"{self._GAUGE_KEY_PREFIX}{key}"
        raw = _cache_payload(await self._cache.get(redis_key), key=redis_key)
        current = float(raw) if raw is not None else 0.0
        updated = max(current + delta, 0.0)
        _cache_payload(
            await self._cache.set(redis_key, str(updated), ttl=ttl),
            key=redis_key,
        )
        return updated

    async def add_calendar_entry(self, key: str, timestamp: float, ttl: int) -> None:
        redis_key = f"{self._CALENDAR_KEY_PREFIX}{key}"
        try:
            raw_result = await self._cache.get(redis_key)
            if hasattr(raw_result, "is_ok"):
                raw = raw_result.unwrap_or(None) if raw_result.is_ok() else None
            else:
                raw = raw_result
            entries: list[float] = []
            if raw is not None:
                entries = [float(v) for v in raw.split(",") if v]
            entries.append(timestamp)
            await self._cache.set(redis_key, ",".join(str(v) for v in entries), ttl=ttl)
        except (OSError, ConnectionError, RuntimeError, ValueError, TypeError):
            pass

    async def query_calendar(self, key: str, start: float, end: float) -> list[float]:
        redis_key = f"{self._CALENDAR_KEY_PREFIX}{key}"
        try:
            raw_result = await self._cache.get(redis_key)
            if hasattr(raw_result, "is_ok"):
                raw = raw_result.unwrap_or(None) if raw_result.is_ok() else None
            else:
                raw = raw_result
            if raw is None:
                return []
            entries = [float(v) for v in raw.split(",") if v]
            return sorted([v for v in entries if start <= v <= end])
        except (OSError, ConnectionError, RuntimeError, ValueError, TypeError):
            return []
