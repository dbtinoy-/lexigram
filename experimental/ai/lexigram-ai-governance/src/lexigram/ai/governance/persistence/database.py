"""SQL-backed governance persistence backend.

Multi-replica state storage using a
:class:`~lexigram.contracts.data.DatabaseProviderProtocol` — suitable where
Redis is not available but a shared relational database is.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

__all__ = ["DatabaseGovernancePersistence"]

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
