"""GraphQL response caching.

This module provides response caching to improve performance
for repeated queries.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
from typing import TYPE_CHECKING, Any

from lexigram import serialization as json
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol


logger = get_logger(__name__)


class _MemoryCacheShim:
    """Local in-memory fallback used when no CacheBackendProtocol is registered in the container.

    Implements the full :class:`~lexigram.contracts.cache.CacheBackendProtocol` protocol so
    that static analysis and runtime ``isinstance`` checks pass.

    .. warning::
        Not suitable for production with multiple process instances — all state is
        in-process memory with no replication or persistence.
    """

    def __init__(self, default_ttl: int = 300) -> None:
        self._store: dict[str, tuple[Any, datetime | None]] = {}
        self._default_ttl = timedelta(seconds=default_ttl)
        self._locks: dict[str, bool] = {}

    def _now(self) -> datetime:
        """Get current timestamp."""
        return ambient_clock.now()

    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        if key not in self._store:
            return None
        value, expires = self._store[key]
        if expires and expires < self._now():
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a value in cache."""
        ttl_delta = timedelta(seconds=ttl) if ttl else self._default_ttl
        expires = self._now() + ttl_delta if ttl else None
        self._store[key] = (value, expires)
        return True

    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        existed = key in self._store
        self._store.pop(key, None)
        return existed

    async def delete_many(self, keys: list[str]) -> bool:
        """Delete multiple values from cache."""
        for key in keys:
            self._store.pop(key, None)
        return True

    async def exists(self, key: str) -> bool:
        """Check whether a key exists in cache."""
        if key not in self._store:
            return False
        _, expires = self._store[key]
        if expires and expires < self._now():
            del self._store[key]
            return False
        return True

    async def clear(self) -> bool:
        """Clear all cache entries."""
        self._store.clear()
        return True

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values from cache."""
        result: dict[str, Any] = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        """Set multiple values in cache."""
        for key, value in items.items():
            await self.set(key, value, ttl)
        return True

    async def acquire_lock(self, key: str, ttl: int) -> bool:
        """Acquire a simple in-memory lock."""
        if self._locks.get(key):
            return False
        self._locks[key] = True
        return True

    async def release_lock(self, key: str) -> bool:
        """Release an in-memory lock."""
        existed = self._locks.pop(key, False)
        return bool(existed)


@dataclass
class ResponseCacheEntry:
    """Cached GraphQL response entry.

    Attributes:
        data: The cached response data.
        extensions: Optional response extensions.
        created_at: When the entry was created.
        ttl: Time-to-live in seconds.
    """

    data: Any
    extensions: dict | None = None
    created_at: datetime | None = None
    ttl: int | None = None


def compute_cache_key(
    query: str,
    variables: dict | None = None,
    operation_name: str | None = None,
    user_id: str | None = None,
    tenant_id: str | None = None,
    query_hash: str | None = None,
) -> str:
    """Compute a deterministic cache key for a GraphQL operation.

    The key incorporates the query, variables, operation name, and optionally
    the user and tenant identifiers so that multi-tenant or user-scoped caches
    cannot cross-contaminate each other's responses.

    When APQ (Automatic Persisted Queries) is enabled, callers should pass the
    pre-computed ``query_hash`` from the APQ extension (SHA-256 hex digest of
    the query string).  This avoids hashing the query twice — once in the APQ
    pipeline and again here.

    Args:
        query: GraphQL query string.
        variables: Query variables.
        operation_name: Optional operation name.
        user_id: Optional user identifier for per-user cache isolation.
        tenant_id: Optional tenant identifier for multi-tenant isolation.
        query_hash: Optional pre-computed SHA-256 hex digest of *query* (e.g.
            from APQ ``extensions.persistedQuery.sha256Hash``).  When provided,
            re-hashing the full query string is skipped.

    Returns:
        Namespaced SHA-256 cache key string.
    """
    # Use the pre-computed hash when available (APQ fast path) to avoid
    # re-hashing the query string.
    base_hash = query_hash or hashlib.sha256(query.encode("utf-8")).hexdigest()
    key_parts = [base_hash]

    if variables:
        key_parts.append(json.dumps(variables, sort_keys=True).decode("utf-8"))

    if operation_name:
        key_parts.append(operation_name)

    if tenant_id:
        key_parts.append(f"t:{tenant_id}")

    if user_id:
        key_parts.append(f"u:{user_id}")

    # Only need a second hash pass when there are extra discriminators beyond
    # the query hash — otherwise base_hash alone is already unique.
    if len(key_parts) == 1:
        return f"gql:{base_hash[:32]}"

    key_string = "|".join(key_parts)
    key_digest = hashlib.sha256(key_string.encode("utf-8")).hexdigest()
    return f"gql:{key_digest[:32]}"


class ResponseCache:
    """GraphQL response cache.

    Caches complete query responses to improve performance for repeated queries.

    This is a **response-level** cache — the entire query result is cached
    keyed on ``(query, variables, operation_name)``.  This is the current
    implementation.

    .. TODO::
        **Field-level caching via ``@CacheControl`` directive** is not yet
        implemented.  The idea is to annotate individual Strawberry fields with
        a ``@CacheControl(max_age=60)`` directive so that only the hot, slow
        resolvers are cached rather than the entire response.  This requires:

        1. A custom Strawberry extension that intercepts field resolution
        2. Generating ``Cache-Control`` HTTP headers from the directive values
           (per the Apollo ``@cacheControl`` spec)
        3. Integrating with :class:`CacheBackendProtocol` for per-field storage

        Until this is implemented, use ``@functools.lru_cache`` or a
        ``CacheBackendProtocol`` call inside individual resolver methods as a workaround.

    Example:
        ```python
        from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol

        cache = ResponseCache(backend=my_cache_backend)

        # Check cache before execution
        key = compute_cache_key(query, variables)
        cached = await cache.get(key)

        if cached:
            return cached

        # Execute query and cache result
        result = await executor.execute(...)
        await cache.set(key, result)
        ```
    """

    def __init__(
        self,
        backend: CacheBackendProtocol,
        enabled: bool = True,
        default_ttl: int = 300,
    ):
        """Initialize the cache.

        Args:
            backend: Cache backend implementation.
            enabled: Whether caching is enabled.
            default_ttl: Default time-to-live in seconds.
        """
        self._backend = backend
        self._enabled = enabled
        self._default_ttl = default_ttl

    @property
    def enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._enabled

    async def get(self, key: str) -> ResponseCacheEntry | None:
        """Get a cached response.

        Args:
            key: Cache key.

        Returns:
            Cached entry if found, None otherwise.
        """
        if not self._enabled:
            return None

        try:
            return await self._backend.get(key)  # type: ignore[return-value]
        except (OSError, LookupError, RuntimeError) as e:
            logger.warning("Cache get failed: %s", e)
            return None

    async def set(
        self,
        key: str,
        data: Any,
        extensions: dict | None = None,
        ttl: int | None = None,
    ) -> None:
        """Cache a response.

        Args:
            key: Cache key.
            data: Response data to cache.
            extensions: Optional response extensions.
            ttl: Optional time-to-live in seconds.
        """
        if not self._enabled:
            return

        try:
            entry = ResponseCacheEntry(
                data=data,
                extensions=extensions,
                created_at=datetime.now(UTC),
                ttl=ttl or self._default_ttl,
            )
            await self._backend.set(key, entry, ttl)
        except (OSError, LookupError, RuntimeError) as e:
            logger.warning("Cache set failed: %s", e)

    async def invalidate(self, key: str) -> None:
        """Invalidate a cached entry.

        Args:
            key: Cache key to invalidate.
        """
        try:
            await self._backend.delete(key)
        except (OSError, LookupError, RuntimeError) as e:
            logger.warning("Cache invalidation failed: %s", e)

    async def clear(self) -> None:
        """Clear all cached entries."""
        try:
            await self._backend.clear()
        except (OSError, LookupError, RuntimeError) as e:
            logger.warning("Cache clear failed: %s", e)


def create_response_cache(
    backend_type: str = "memory",
    **kwargs: Any,
) -> ResponseCache:
    """Create a response cache with the specified backend.

    Args:
        backend_type: Type of backend ('memory').
        **kwargs: Additional arguments for the backend.

    Returns:
        Configured ResponseCache.
    """
    if backend_type == "memory":
        backend: CacheBackendProtocol = _MemoryCacheShim(**kwargs)  # type: ignore[assignment]
    else:
        raise ValueError(f"Unknown cache backend type: {backend_type}")

    return ResponseCache(backend=backend)


__all__ = [
    "ResponseCache",
    "ResponseCacheEntry",
    "compute_cache_key",
    "create_response_cache",
]
