"""Persistence backends for AI governance state.

Defines the :class:`GovernancePersistence` protocol and two concrete
implementations:

- :class:`InMemoryGovernancePersistence` — process-local state, suitable for
  development, testing, and single-instance deployments.
- :class:`RedisGovernancePersistence` — distributed state backed by a
  :class:`~lexigram.contracts.cache.CacheBackendProtocol`, enabling multi-replica
  consistency for rate limiting and budget enforcement.

The :class:`~lexigram.ai.governance.manager.AIGovernanceManager` accepts any
implementation via constructor injection so the storage strategy is swappable
without changing governance logic.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

from lexigram.ai.governance.exceptions import GovernancePersistenceError

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol
    from lexigram.contracts.infra.cache import CacheBackendProtocol
    from lexigram.contracts.infra.cache.exceptions import CacheError
    from lexigram.result import Result

__all__ = [
    "DatabaseGovernancePersistence",
    "GovernancePersistence",
    "InMemoryGovernancePersistence",
    "RedisGovernancePersistence",
]


@runtime_checkable
class GovernancePersistence(Protocol):
    """Storage protocol for governance counters and spend tallies.

    Implementations must be safe for concurrent async access.  All methods
    are *coroutines* to allow either local (in-process) or remote (Redis,
    database) storage without changing the call-site.
    """

    async def incr_requests(
        self,
        key: str,
        window: float,
    ) -> int:
        """Record a new request and return the request count within the window.

        Args:
            key: Bucket key (e.g. ``"global"`` or a user/tenant id).
            window: Rolling window size in seconds.

        Returns:
            Number of requests (including the current one) inside the window.
        """
        ...

    async def add_spend(
        self,
        key: str,
        amount: float,
        ttl: int,
    ) -> float:
        """Add ``amount`` to the spend accumulator and return the new total.

        Args:
            key: Bucket key (e.g. ``"global:2025-06"``).
            amount: Cost amount to add.
            ttl: Time-to-live for the accumulator entry in seconds.

        Returns:
            Updated total spend.
        """
        ...

    async def get_spend(self, key: str) -> float:
        """Return the current accumulated spend for *key*.

        Args:
            key: Bucket key.

        Returns:
            Current spend; ``0.0`` if no data recorded.
        """
        ...

    # -- Gauge methods -------------------------------------------------------

    async def read_gauge(self, key: str) -> float:
        """Read the current gauge value for *key*.

        Args:
            key: Gauge key (e.g. ``"tenant:gpt4:remaining"``).

        Returns:
            Current gauge value; ``0.0`` if no data recorded.
        """
        ...

    async def write_gauge(self, key: str, value: float, ttl: int) -> None:
        """Set the gauge *value* for *key* with a TTL.

        Args:
            key: Gauge key.
            value: Float gauge value.
            ttl: Time-to-live in seconds.
        """
        ...

    async def incr_gauge(self, key: str, delta: float, ttl: int) -> float:
        """Atomically increment (or decrement) the gauge for *key*.

        Args:
            key: Gauge key.
            delta: Amount to add (can be negative).
            ttl: Time-to-live in seconds.

        Returns:
            The gauge value after applying *delta*.
        """
        ...

    # -- Calendar methods ----------------------------------------------------

    async def add_calendar_entry(self, key: str, timestamp: float, ttl: int) -> None:
        """Record a timestamp entry in a calendar-style bucket.

        Args:
            key: Calendar bucket key.
            timestamp: Unix timestamp to record.
            ttl: Time-to-live in seconds for the bucket.
        """
        ...

    async def query_calendar(self, key: str, start: float, end: float) -> list[float]:
        """Return all timestamps in *key* that fall within [*start*, *end*].

        Args:
            key: Calendar bucket key.
            start: Unix timestamp, start of range (inclusive).
            end: Unix timestamp, end of range (inclusive).

        Returns:
            List of matching timestamps (chronological order).
        """
        ...

    async def decr_gauge(self, key: str, amount: float, ttl: int) -> float:
        """Decrement a gauge key by *amount*.

        Default implementation delegates to :meth:`incr_gauge` with a
        negative delta.
        """
        return await self.incr_gauge(key, -amount, ttl)

    async def incr_calendar(
        self, key: str, period: str, amount: float, ttl: int
    ) -> float:
        """Accumulate *amount* in a calendar-window bucket.

        Delegates to :meth:`add_spend` with a period-scoped key (``key`` +
        ``:`` + ``period``).
        """
        return await self.add_spend(f"{key}:{period}", amount, ttl)

    async def get_calendar(self, key: str, period: str) -> float:
        """Read the calendar-window accumulator for *key* + *period*.

        Delegates to :meth:`get_spend` with a period-scoped key.
        """
        return await self.get_spend(f"{key}:{period}")


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------


class InMemoryGovernancePersistence:
    """Process-local governance persistence using plain Python dicts.

    Request counts are tracked with a sliding-window approach (list of
    monotonic timestamps).  Spend totals are stored as plain floats.

    This implementation is **not** suitable for multi-process or
    multi-replica deployments.  Use :class:`RedisGovernancePersistence`
    in production.
    """

    def __init__(self) -> None:
        self._request_buckets: dict[str, list[float]] = {}
        self._spend_totals: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._calendar: dict[str, list[tuple[float, float]]] = {}

    async def incr_requests(self, key: str, window: float) -> int:
        now = time.monotonic()
        bucket = self._request_buckets.setdefault(key, [])
        # Prune entries outside the window, then record current request
        self._request_buckets[key] = [t for t in bucket if now - t <= window]
        self._request_buckets[key].append(now)
        return len(self._request_buckets[key])

    async def add_spend(self, key: str, amount: float, ttl: int) -> float:
        current = self._spend_totals.get(key, 0.0)
        updated = current + amount
        self._spend_totals[key] = updated
        return updated

    async def get_spend(self, key: str) -> float:
        return self._spend_totals.get(key, 0.0)

    async def read_gauge(self, key: str) -> float:
        return self._gauges.get(key, 0.0)

    async def write_gauge(self, key: str, value: float, ttl: int) -> None:
        self._gauges[key] = value

    async def incr_gauge(self, key: str, delta: float, ttl: int) -> float:
        current = self._gauges.get(key, 0.0)
        updated = max(current + delta, 0.0)
        self._gauges[key] = updated
        return updated

    async def add_calendar_entry(self, key: str, timestamp: float, ttl: int) -> None:
        now = time.monotonic()
        bucket = self._calendar.setdefault(key, [])
        bucket.append((now, timestamp))

    async def query_calendar(self, key: str, start: float, end: float) -> list[float]:
        results = []
        bucket = self._calendar.get(key, [])
        for _, ts in bucket:
            if start <= ts <= end:
                results.append(ts)
        return results


# ---------------------------------------------------------------------------
# Redis-backed implementation
# ---------------------------------------------------------------------------

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
        raw_val = _cache_payload(
            await self._cache.get(counter_key), key=counter_key
        )
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


# ---------------------------------------------------------------------------
# Database-backed implementation
# ---------------------------------------------------------------------------

_CREATE_REQUESTS_TABLE = """
CREATE TABLE IF NOT EXISTS ai_governance_requests (
    id  INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT    NOT NULL,
    ts  REAL    NOT NULL
)
"""

_CREATE_SPEND_TABLE = """
CREATE TABLE IF NOT EXISTS ai_governance_spend (
    key        TEXT NOT NULL PRIMARY KEY,
    amount     REAL NOT NULL DEFAULT 0,
    expires_at REAL NOT NULL
)
"""

_INSERT_REQUEST = "INSERT INTO ai_governance_requests (key, ts) VALUES (?, ?)"
_DELETE_EXPIRED_REQUESTS = "DELETE FROM ai_governance_requests WHERE key = ? AND ts < ?"
_COUNT_REQUESTS = "SELECT COUNT(*) AS cnt FROM ai_governance_requests WHERE key = ?"

_UPSERT_SPEND = (
    "INSERT INTO ai_governance_spend (key, amount, expires_at) VALUES (?, ?, ?) "
    "ON CONFLICT (key) DO UPDATE SET "
    "amount = amount + excluded.amount, "
    "expires_at = excluded.expires_at"
)

_GET_SPEND = "SELECT amount FROM ai_governance_spend WHERE key = ? AND expires_at >= ?"

_GAUGE_TABLE = """
CREATE TABLE IF NOT EXISTS ai_governance_gauges (
    key        TEXT NOT NULL PRIMARY KEY,
    value      REAL NOT NULL DEFAULT 0.0,
    expires_at REAL NOT NULL
)
"""
_UPSERT_GAUGE = (
    "INSERT INTO ai_governance_gauges (key, value, expires_at) VALUES (?, ?, ?) "
    "ON CONFLICT (key) DO UPDATE SET "
    "value = excluded.value, "
    "expires_at = excluded.expires_at"
)
_GET_GAUGE = "SELECT value FROM ai_governance_gauges WHERE key = ? AND expires_at >= ?"

_CALENDAR_TABLE = """
CREATE TABLE IF NOT EXISTS ai_governance_calendar (
    id  INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT    NOT NULL,
    ts  REAL    NOT NULL
)
"""
_INSERT_CALENDAR = "INSERT INTO ai_governance_calendar (key, ts) VALUES (?, ?)"
_QUERY_CALENDAR = (
    "SELECT ts FROM ai_governance_calendar "
    "WHERE key = ? AND ts >= ? AND ts <= ? ORDER BY ts ASC"
)


class DatabaseGovernancePersistence:
    """SQL-backed governance persistence using :class:`~lexigram.contracts.data.DatabaseProviderProtocol`.

    Stores request timestamps in ``ai_governance_requests`` and spend totals
    in ``ai_governance_spend``.  Both tables are created lazily on first use.

    This backend is suitable for multi-replica deployments where Redis is not
    available but a shared relational database is.  Row-level locking provided
    by the database engine ensures counter consistency.

    Args:
        db: A connected :class:`~lexigram.contracts.data.DatabaseProviderProtocol`
            resolved from the DI container.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self._db = db
        self._initialised = False

    async def _ensure_tables(self) -> None:
        """Create governance tables if they do not yet exist."""
        if not self._initialised:
            await self._db.execute(_CREATE_REQUESTS_TABLE)
            await self._db.execute(_CREATE_SPEND_TABLE)
            await self._db.execute(_GAUGE_TABLE)
            await self._db.execute(_CALENDAR_TABLE)
            self._initialised = True

    async def incr_requests(self, key: str, window: float) -> int:
        """Insert current timestamp, prune expired rows, return window count.

        Args:
            key: Governance bucket key.
            window: Rolling window size in seconds.

        Returns:
            Number of requests within *window* (including the current one).
        """
        await self._ensure_tables()
        now = time.time()
        cutoff = now - window
        await self._db.execute(_INSERT_REQUEST, [key, now])
        await self._db.execute(_DELETE_EXPIRED_REQUESTS, [key, cutoff])
        result = await self._db.execute_query(_COUNT_REQUESTS, [key])
        rows = result.rows
        return int(rows[0]["cnt"]) if rows else 1

    async def add_spend(self, key: str, amount: float, ttl: int) -> float:
        """Accumulate *amount* against *key* and return the running total.

        The row is upserted with ``expires_at = now + ttl``; callers should
        use time-period-scoped keys (e.g. ``"global:2025-06"``) so that
        distinct budget periods never collide.

        Args:
            key: Governance bucket key.
            amount: Cost to add.
            ttl: Seconds until the entry should expire.

        Returns:
            Updated running total for *key*.
        """
        await self._ensure_tables()
        expires_at = time.time() + ttl
        await self._db.execute(_UPSERT_SPEND, [key, amount, expires_at])
        result = await self._db.execute_query(_GET_SPEND, [key, time.time()])
        rows = result.rows
        return float(rows[0]["amount"]) if rows else amount

    async def get_spend(self, key: str) -> float:
        """Return the current accumulated spend for *key*.

        Args:
            key: Governance bucket key.

        Returns:
            Current spend; ``0.0`` if no data recorded or entry has expired.
        """
        await self._ensure_tables()
        result = await self._db.execute_query(_GET_SPEND, [key, time.time()])
        rows = result.rows
        return float(rows[0]["amount"]) if rows else 0.0

    async def read_gauge(self, key: str) -> float:
        """Read the current gauge value for *key*."""
        await self._ensure_tables()
        result = await self._db.execute_query(_GET_GAUGE, [key, time.time()])
        rows = result.rows
        return float(rows[0]["value"]) if rows else 0.0

    async def write_gauge(self, key: str, value: float, ttl: int) -> None:
        """Set the gauge *value* for *key* with a TTL."""
        await self._ensure_tables()
        expires_at = time.time() + ttl
        await self._db.execute(_UPSERT_GAUGE, [key, value, expires_at])

    async def incr_gauge(self, key: str, delta: float, ttl: int) -> float:
        """Atomically increment (or decrement) the gauge for *key*."""
        await self._ensure_tables()
        now = time.time()
        result = await self._db.execute_query(_GET_GAUGE, [key, now])
        rows = result.rows
        current = float(rows[0]["value"]) if rows else 0.0
        updated = max(current + delta, 0.0)
        expires_at = now + ttl
        await self._db.execute(_UPSERT_GAUGE, [key, updated, expires_at])
        return updated

    async def add_calendar_entry(self, key: str, timestamp: float, ttl: int) -> None:
        """Record a timestamp entry in a calendar-style bucket."""
        await self._ensure_tables()
        await self._db.execute(_INSERT_CALENDAR, [key, timestamp])

    async def query_calendar(self, key: str, start: float, end: float) -> list[float]:
        """Return all timestamps in *key* that fall within range."""
        await self._ensure_tables()
        result = await self._db.execute_query(_QUERY_CALENDAR, [key, start, end])
        rows = result.rows
        return [float(r["ts"]) for r in rows] if rows else []
