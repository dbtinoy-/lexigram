"""Persistence backends for AI governance state.

Defines the :class:`GovernancePersistence` storage protocol shared by the
concrete backend modules:

- :class:`InMemoryGovernancePersistence` — process-local state, suitable for
  development, testing, and single-instance deployments.
- :class:`RedisGovernancePersistence` — distributed state backed by a
  :class:`~lexigram.contracts.cache.CacheBackendProtocol`, enabling multi-replica
  consistency for rate limiting and budget enforcement.
- :class:`DatabaseGovernancePersistence` — SQL-backed state via a
  :class:`~lexigram.contracts.data.DatabaseProviderProtocol` for deployments
  where Redis is unavailable.

The :class:`~lexigram.ai.governance.manager.AIGovernanceManager` accepts any
implementation via constructor injection so the storage strategy is swappable
without changing governance logic.  This module re-exports every backend so
the original import path remains valid.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lexigram.ai.governance.persistence.database import (
    DatabaseGovernancePersistence as DatabaseGovernancePersistence,
)
from lexigram.ai.governance.persistence.in_memory import (
    InMemoryGovernancePersistence as InMemoryGovernancePersistence,
)
from lexigram.ai.governance.persistence.redis_backend import (
    RedisGovernancePersistence as RedisGovernancePersistence,
)

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
