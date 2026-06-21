"""Automatic Persisted Queries (APQ) for GraphQL.

This module provides APQ support to reduce bandwidth by allowing clients
to send query hashes instead of full query strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, runtime_checkable

from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.security.hashing import ambient as hashing

logger = get_logger(__name__)


@runtime_checkable
class PersistedQueryStore(Protocol):
    """Store for persisted query mappings.

    Implement this protocol to provide custom storage for persisted queries.
    """

    async def get(self, hash: str) -> str | None:
        """Get a query by its hash.

        Args:
            hash: SHA256 hash of the query.

        Returns:
            The query string if found, None otherwise.
        """
        ...

    async def put(self, hash: str, query: str) -> None:
        """Store a query with its hash.

        Args:
            hash: SHA256 hash of the query.
            query: The full query string.
        """
        ...


class InMemoryPersistedQueryStore:
    """In-memory implementation of PersistedQueryStore.

    Warning: Not suitable for production use with multiple instances.
    Use RedisPersistedQueryStore for production deployments.
    """

    def __init__(self, ttl_seconds: int | None = None):
        """Initialize the store.

        Args:
            ttl_seconds: Optional time-to-live for entries in seconds.
        """
        self._store: dict[str, tuple[str, datetime | None]] = {}
        self._ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else None

    def _now(self) -> datetime:
        return ambient_clock.now()

    async def get(self, hash: str) -> str | None:
        """Get a query by its hash."""
        if hash not in self._store:
            return None

        query, expires = self._store[hash]

        # Check expiration
        if expires and expires < self._now():
            del self._store[hash]
            return None

        return query

    async def put(self, hash: str, query: str) -> None:
        """Store a query with its hash."""
        expires = self._now() + self._ttl if self._ttl else None
        self._store[hash] = (query, expires)

    def clear(self) -> None:
        """Clear all stored queries."""
        self._store.clear()


class RedisPersistedQueryStore:
    """Redis-backed implementation of PersistedQueryStore.

    Suitable for production use with multiple application instances.
    """

    def __init__(
        self,
        redis_client: Any,
        key_prefix: str = "graphql:apq:",
        ttl_seconds: int = 86400,  # 24 hours default
    ):
        """Initialize the store.

        Args:
            redis_client: Redis client instance (aioRedis or redis-py async).
            key_prefix: Prefix for Redis keys.
            ttl_seconds: Time-to-live for entries in seconds.
        """
        self._redis = redis_client
        self._prefix = key_prefix
        self._ttl = ttl_seconds

    async def get(self, hash: str) -> str | None:
        """Get a query by its hash."""
        key = f"{self._prefix}{hash}"
        try:
            result = await self._redis.get(key)
            return result.decode("utf-8") if result else None
        except (OSError, RuntimeError, AttributeError) as e:
            logger.warning("Redis get failed for APQ: %s", e)
            return None

    async def put(self, hash: str, query: str) -> None:
        """Store a query with its hash."""
        key = f"{self._prefix}{hash}"
        try:
            await self._redis.setex(key, self._ttl, query)
        except (OSError, RuntimeError) as e:
            logger.warning("Redis put failed for APQ: %s", e)


class CacheBackendPersistedQueryStore:
    """CacheBackendProtocol-backed APQ store for multi-process deployments.

    Uses the platform's :class:`~lexigram.contracts.cache.CacheBackendProtocol`
    abstraction rather than a raw Redis client — compatible with any
    configured cache provider (Redis, Memcached, etc.) without coupling
    this package to a specific driver.

    Suitable for production use with multiple application instances.
    """

    def __init__(
        self,
        cache: Any,
        key_prefix: str = "graphql:apq:",
        ttl_seconds: int = 86400,
    ) -> None:
        """Initialize the store.

        Args:
            cache: A :class:`~lexigram.contracts.cache.CacheBackendProtocol` instance.
            key_prefix: Prefix applied to all cache keys.
            ttl_seconds: Time-to-live for stored entries in seconds.
        """
        self._cache = cache
        self._prefix = key_prefix
        self._ttl = ttl_seconds

    async def get(self, hash: str) -> str | None:
        """Get a query by its hash."""
        key = f"{self._prefix}{hash}"
        try:
            cached: str | None = await self._cache.get(key)
            return cached
        except (OSError, LookupError, RuntimeError) as e:
            logger.warning("cache_apq_get_failed", key=key, error=str(e))
            return None

    async def put(self, hash: str, query: str) -> None:
        """Store a query with its hash."""
        key = f"{self._prefix}{hash}"
        try:
            await self._cache.set(key, query, ttl=self._ttl)
        except (OSError, LookupError, RuntimeError) as e:
            logger.warning("cache_apq_put_failed", key=key, error=str(e))


@dataclass
class APQResult:
    """Result of APQ lookup.

    Attributes:
        query: The full query string (if found).
        is_persisted: Whether the query was found in the store.
        hash: The hash used for lookup.
    """

    query: str | None = None
    is_persisted: bool = False
    hash: str = ""


def compute_query_hash(query: str) -> str:
    """Compute SHA256 hash of a GraphQL query.

    Uses Sha256Hasher for wire compatibility with persisted queries.
    The algorithm must remain SHA256 to ensure client-server compatibility.

    Args:
        query: The GraphQL query string.

    Returns:
        Hex-encoded SHA256 hash.
    """
    return hashing.hash_hex(query)


class APQHandler:
    """Handler for Automatic Persisted Queries.

    Implements the APQ protocol:
    1. Client sends query hash → Server looks up full query
    2. If not found, client sends hash + full query → Server stores
    3. Subsequent requests use just the hash
    """

    def __init__(
        self,
        store: PersistedQueryStore,
        enabled: bool = True,
    ):
        """Initialize the APQ handler.

        Args:
            store: Persisted query store implementation.
            enabled: Whether APQ is enabled.
        """
        self._store = store
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        """Check if APQ is enabled."""
        return self._enabled

    async def resolve_query(
        self,
        query: str | None,
        extensions: dict | None = None,
    ) -> APQResult:
        """Resolve the full query using APQ.

        Args:
            query: The query from the request (may be None for hash-only).
            extensions: The extensions from the GraphQL request.

        Returns:
            APQResult with the resolved query.
        """
        if not self._enabled:
            return APQResult(query=query, is_persisted=False)

        # Check for APQ extension data
        apq_ext = None
        if extensions and "persistedQuery" in extensions:
            apq_ext = extensions["persistedQuery"]

        # Case 1: No query, no APQ extension → error
        if not query and not apq_ext:
            return APQResult(query=query, is_persisted=False)

        # Case 2: Has full query, no APQ → store it
        if query and not apq_ext:
            hash_value = compute_query_hash(query)
            await self._store.put(hash_value, query)
            return APQResult(query=query, hash=hash_value, is_persisted=False)

        # Case 3: Has APQ extension
        if apq_ext:
            # Get the hash
            hash_value = apq_ext.get("sha256Hash")
            if not hash_value:
                return APQResult(query=query, is_persisted=False)

            # Try to look up the query
            stored_query = await self._store.get(hash_value)

            if stored_query:
                # Cache hit
                return APQResult(query=stored_query, hash=hash_value, is_persisted=True)

            # Cache miss - client should send the full query
            if not query:
                # Client needs to send the full query
                return APQResult(hash=hash_value, is_persisted=False)

            # Client sent both hash and query - store it
            await self._store.put(hash_value, query)
            return APQResult(query=query, hash=hash_value, is_persisted=False)

        return APQResult(query=query, is_persisted=False)

    def create_extension_response(self, hash: str) -> dict:
        """Create the APQ extension response.

        Args:
            hash: The query hash.

        Returns:
            Extension dict for the GraphQL response.
        """
        return {
            "persistedQuery": {
                "sha256Hash": hash,
                "version": 1,
            },
        }


# Default APQ handler factory
def create_apq_handler(
    store_type: str = "memory",
    **kwargs: Any,
) -> APQHandler:
    """Create an APQ handler with the specified store.

    Args:
        store_type: Type of store ('memory' or 'redis').
        **kwargs: Additional arguments for the store.

    Returns:
        Configured APQHandler.
    """
    store: PersistedQueryStore
    if store_type == "memory":
        store = InMemoryPersistedQueryStore(**kwargs)
    elif store_type == "redis":
        store = RedisPersistedQueryStore(**kwargs)
    else:
        raise ValueError(f"Unknown APQ store type: {store_type}")

    return APQHandler(store=store)


__all__ = [
    "APQHandler",
    "APQResult",
    "InMemoryPersistedQueryStore",
    "PersistedQueryStore",
    "RedisPersistedQueryStore",
    "compute_query_hash",
    "create_apq_handler",
]
