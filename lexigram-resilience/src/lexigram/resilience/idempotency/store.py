"""In-memory idempotency store for deduplicating operations.

Provides a pluggable storage backend for tracking idempotency keys, ensuring
that operations with the same key are executed at most once within a TTL window.
Suitable for development, testing, and single-instance deployments.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from lexigram.concurrency.task_utils import create_tracked_task
from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol
from lexigram.contracts.domain.idempotency import IdempotencyRecord, IdempotencyStatus
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock

logger = get_logger(__name__)


class InMemoryIdempotencyStore:
    """In-memory implementation of IdempotencyStoreProtocol with TTL-based expiry.

    Stores results in a dictionary keyed by idempotency key, with optional
    expiry timestamps. Suitable for development and testing.
    """

    def __init__(
        self,
        auto_cleanup_interval: float | None = None,
        max_entries: int | None = None,
    ) -> None:
        """Create an in-memory idempotency store.

        Args:
            auto_cleanup_interval: Seconds between automatic purges of expired
                entries.  When set, a background task starts immediately.
            max_entries: Maximum number of entries the store will hold.  When
                the cap is reached, the *oldest* (first-inserted) unexpired
                entry is evicted before the new one is stored.  ``None``
                means the store grows without bound.
        """
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._key_locks: dict[str, asyncio.Lock] = {}
        self._key_events: dict[str, asyncio.Event] = {}
        self._auto_cleanup_interval = auto_cleanup_interval
        self._max_entries = max_entries
        self._cleanup_task: asyncio.Task[None] | None = None
        self._background_tasks: set[asyncio.Task[Any]] = set()
        if auto_cleanup_interval is not None:
            self._cleanup_task = create_tracked_task(
                self._cleanup_loop(),
                self._background_tasks,
                name=f"idempotency_cleanup_{id(self)}",
            )

    async def get(self, key: str) -> Any | None:
        """Retrieve a stored result, returning None if expired or missing.

        Args:
            key: The idempotency key.

        Returns:
            The stored result, or None if not found or expired.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and ambient_clock.monotonic() > expires_at:
            del self._store[key]
            return None
        if value is IdempotencyStatus.PENDING:
            event = self._key_events.get(key)
            if event is not None:
                await event.wait()
                entry = self._store.get(key)
                if entry is None:
                    return None
                value, _ = entry
            else:
                return None
        return value

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store a result with optional TTL.

        If *max_entries* was configured and storing *key* would exceed the
        cap, the oldest entry is evicted first (FIFO order).  Updating an
        existing key never triggers eviction.

        Args:
            key: The idempotency key.
            value: The result value to cache.
            ttl: Time-to-live in seconds, or None for no expiry.
        """
        if (
            self._max_entries is not None
            and key not in self._store
            and len(self._store) >= self._max_entries
        ):
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]
            logger.debug("idempotency.evicted", key=oldest_key, reason="max_entries")
        expires_at = (ambient_clock.monotonic() + ttl) if ttl is not None else None
        self._store[key] = (value, expires_at)
        logger.debug("idempotency.stored", key=key, ttl=ttl)
        event = self._key_events.pop(key, None)
        if event is not None:
            event.set()

    async def delete(self, key: str) -> None:
        """Remove a stored idempotency record.

        Args:
            key: The idempotency key to remove.
        """
        self._store.pop(key, None)

    async def acquire(self, key: str, ttl: int) -> bool:
        """Atomically claim an idempotency key if not already held.

        Uses a per-key ``asyncio.Lock`` to guarantee in-process atomicity.
        Returns ``True`` if this coroutine was the first to claim the key and
        should proceed with execution; ``False`` if the key already existed.

        Args:
            key: The idempotency key to acquire.
            ttl: Time-to-live in seconds for the claimed key.

        Returns:
            ``True`` if the key was freshly claimed; ``False`` if already held.
        """
        if key not in self._key_locks:
            self._key_locks[key] = asyncio.Lock()
        async with self._key_locks[key]:
            if (existing := self._store.get(key)) is not None:
                _, expires_at = existing
                if expires_at is None or ambient_clock.monotonic() <= expires_at:
                    return False
            self._key_events[key] = asyncio.Event()
            expires_at = ambient_clock.monotonic() + ttl
            self._store[key] = (IdempotencyStatus.PENDING, expires_at)
            logger.debug("idempotency.acquired", key=key, ttl=ttl)
            return True

    def clear(self) -> None:
        """Remove all stored idempotency records."""
        self._store.clear()

    async def get_record(self, key: str) -> IdempotencyRecord | None:
        """Retrieve the full idempotency record for *key*, or None.

        Returns an :class:`~lexigram.contracts.domain.idempotency.IdempotencyRecord`
        with a snapshot of the stored entry's value, creation time, expiry,
        and status.  Returns ``None`` when the key is absent or expired.

        Args:
            key: The idempotency key to look up.

        Returns:
            An ``IdempotencyRecord`` if the key exists and has not expired,
            otherwise ``None``.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        now_monotonic = ambient_clock.monotonic()
        if expires_at is not None and now_monotonic > expires_at:
            del self._store[key]
            return None
        now_wall = datetime.now(tz=UTC)
        if expires_at is not None:
            remaining = expires_at - now_monotonic
            expires_wall = datetime.fromtimestamp(
                now_wall.timestamp() + remaining, tz=UTC
            )
        else:
            expires_wall = datetime(9999, 12, 31, tzinfo=UTC)
        status = (
            IdempotencyStatus.PENDING
            if value is IdempotencyStatus.PENDING
            else IdempotencyStatus.COMPLETE
        )
        return IdempotencyRecord(
            key=key,
            result=None if status == IdempotencyStatus.PENDING else value,
            created_at=now_wall,
            expires_at=expires_wall,
            status=status,
        )

    async def start_auto_cleanup(self, interval: float | None = None) -> None:
        """Enable periodic expiry of old entries.

        Args:
            interval: Optional override for the cleanup interval in seconds.
                If not provided, the value passed to the constructor is used.
        """
        if interval is not None:
            self._auto_cleanup_interval = interval
        if self._auto_cleanup_interval is None:
            raise ValueError("cleanup interval not configured")
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = create_tracked_task(
                self._cleanup_loop(),
                self._background_tasks,
                name=f"idempotency_cleanup_{id(self)}",
            )

    async def _cleanup_loop(self) -> None:
        while True:
            assert self._auto_cleanup_interval is not None  # noqa: S101  # loop only started when interval set
            await asyncio.sleep(self._auto_cleanup_interval)
            await self.cleanup_expired()

    async def stop_auto_cleanup(self) -> None:
        """Cancel the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

    @property
    def size(self) -> int:
        """Return the number of stored idempotency records (including expired).

        Returns:
            The total entry count.
        """
        return len(self._store)

    async def has(self, key: str) -> bool:
        """Check whether a non-expired entry exists for the given key.

        Args:
            key: The idempotency key.

        Returns:
            True if the key is present and not expired.
        """
        result = await self.get(key)
        return result is not None

    async def cleanup_expired(self) -> int:
        """Remove all expired entries and return how many were purged.

        Returns:
            The number of entries removed.
        """
        now = ambient_clock.monotonic()
        expired_keys = [
            key
            for key, (_, expires_at) in self._store.items()
            if expires_at is not None and now > expires_at
        ]
        for key in expired_keys:
            del self._store[key]
        if expired_keys:
            logger.debug("idempotency.cleanup", removed=len(expired_keys))
        return len(expired_keys)

    def get_stats(self) -> dict[str, int]:
        """Return basic statistics about the store.

        Returns:
            A dict with ``total`` (all entries), ``active`` (non-expired),
            and ``expired`` counts.
        """
        now = ambient_clock.monotonic()
        expired = sum(
            1
            for _, expires_at in self._store.values()
            if expires_at is not None and now > expires_at
        )
        total = len(self._store)
        return {
            "total": total,
            "active": total - expired,
            "expired": expired,
        }


__all__ = [
    "IdempotencyStoreProtocol",
    "InMemoryIdempotencyStore",
]
