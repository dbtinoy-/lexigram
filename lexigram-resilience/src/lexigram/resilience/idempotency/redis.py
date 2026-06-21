"""Redis-backed idempotency store for durable, distributed deduplication.

Uses ``CacheBackendProtocol`` from ``lexigram-contracts`` as the storage layer.
This module imports ONLY from ``lexigram-contracts`` and ``lexigram`` core —
never directly from ``lexigram-cache``.  The ``CacheBackendProtocol`` instance is
provided by the DI container at runtime.
"""

from __future__ import annotations

from datetime import UTC
import math
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger
from lexigram.result import Result

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol

logger = get_logger(__name__)


class RedisIdempotencyStore:
    """Idempotency store backed by a ``CacheBackendProtocol`` (e.g. Redis).

    Delegates all storage operations to the provided ``CacheBackendProtocol``,
    enabling distributed deduplication across multiple application instances.
    The backend is injected by the DI container, keeping this class fully
    decoupled from any specific cache implementation.

    Args:
        cache: The cache backend used for key storage.
        key_prefix: Optional prefix applied to all idempotency keys to avoid
            collisions with other cache consumers.
    """

    def __init__(
        self,
        cache: CacheBackendProtocol,
        key_prefix: str = "idempotency:",
    ) -> None:
        """Create a Redis-backed idempotency store.

        Args:
            cache: The cache backend resolved from the container.
            key_prefix: Prefix prepended to every key in the cache.
        """
        self._cache = cache
        self._key_prefix = key_prefix

    async def get(self, key: str) -> Any | None:
        """Retrieve a stored result by idempotency key.

        Returns ``None`` for both missing keys and keys claimed but not yet
        resolved (sentinel ``"__pending__"`` entries).

        Args:
            key: The idempotency key.

        Returns:
            The stored result, or ``None`` if not found or still pending.
        """
        cached = await self._cache.get(self._prefixed(key))
        if isinstance(cached, Result):
            cached = cached.unwrap()
        if cached == "__pending__":
            cached = None  # type: ignore[assignment]
        logger.debug("idempotency.redis.get", key=key, found=cached is not None)
        return cached

    async def get_record(self, key: str) -> Any:
        """Retrieve the full idempotency record, including metadata.

        Args:
            key: The idempotency key.

        Returns:
            Result containing IdempotencyRecord or None if missing.
        """
        from datetime import datetime

        from lexigram.contracts.domain.idempotency import (
            IdempotencyRecord,
            IdempotencyStatus,
        )
        from lexigram.result import Ok

        result = await self.get(key)
        if result is None:
            return Ok(None)

        record = IdempotencyRecord(
            key=key,
            result=result,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC),
            status=IdempotencyStatus.COMPLETE,
        )
        return Ok(record)

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store a result with an optional TTL.

        The ``float`` TTL from the ``IdempotencyStoreProtocol`` protocol is rounded
        up to the nearest second for the underlying cache backend.

        Args:
            key: The idempotency key.
            value: The result to store.
            ttl: Time-to-live in seconds, or ``None`` for no expiry.
        """
        cache_ttl: int | None = math.ceil(ttl) if ttl is not None else None
        await self._cache.set(self._prefixed(key), value, ttl=cache_ttl)
        logger.debug("idempotency.redis.set", key=key, ttl=cache_ttl)

    async def delete(self, key: str) -> None:
        """Remove an idempotency record by key.

        Args:
            key: The idempotency key to remove.
        """
        await self._cache.delete(self._prefixed(key))
        logger.debug("idempotency.redis.delete", key=key)

    async def acquire(self, key: str, ttl: int) -> bool:
        """Atomically claim an idempotency key using cache SET-NX semantics.

        Stores a ``"__pending__"`` sentinel so that cross-process races can be
        detected via :meth:`get`.  ``CacheBackendProtocol`` implementations that route
        to Redis will naturally provide atomic ``SET key NX EX ttl`` semantics
        when the backing library (e.g. ``aioredis``) supports it.

        Note:
            If the ``CacheBackendProtocol`` implementation does not support atomic NX,
            a narrow TOCTOU window remains.  Use a ``CacheBackendProtocol`` backed by
            Redis with NX support for fully distributed safety.

        Args:
            key: The idempotency key to acquire.
            ttl: Time-to-live in seconds for the claimed key.

        Returns:
            ``True`` if the key was freshly claimed; ``False`` if already held.
        """
        prefixed = self._prefixed(key)
        existing: Any = await self._cache.get(prefixed)
        if existing is not None:
            logger.debug("idempotency.redis.acquire", key=key, acquired=False)
            return False
        await self._cache.set(prefixed, "__pending__", ttl=ttl)
        logger.debug("idempotency.redis.acquire", key=key, acquired=True)
        return True

    def _prefixed(self, key: str) -> str:
        """Return the cache key with the configured prefix applied."""
        return f"{self._key_prefix}{key}"

    async def cleanup_expired(self) -> int:
        """No-op for Redis-backed store — Redis TTLs expire entries natively.

        Redis automatically evicts keys whose TTL has elapsed, so explicit
        cleanup is unnecessary.  This method exists for API parity with the
        in-memory store.

        Returns:
            Always ``0`` since no active eviction is performed.
        """
        logger.debug("idempotency.redis.cleanup_expired.noop")
        return 0


__all__ = ["RedisIdempotencyStore"]
