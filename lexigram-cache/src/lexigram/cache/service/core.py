"""Core cache service implementation for Lexigram Framework.

Provides :class:`CacheService` — the main high-level caching interface.
Advanced patterns live in sibling modules that are composed via mixin
inheritance:

- :mod:`lexigram.cache.service.pipeline` — batch ``get_many`` / ``set_many``
- :mod:`lexigram.cache.service.invalidation` — tag-based invalidation
- :mod:`lexigram.cache.service.patterns` — cache-aside, stampede protection
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
import random
from typing import TYPE_CHECKING, Any, TypeVar, cast

from lexigram.cache.config import CacheOperationConfig, default_cache_config
from lexigram.cache.service.invalidation import InvalidationMixin
from lexigram.cache.service.patterns import PatternsMixin
from lexigram.cache.service.pipeline import PipelineMixin
from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.primitives.context import REQUEST_ID, Context

if TYPE_CHECKING:
    from lexigram.cache.di.provider import CacheProvider
    from lexigram.cache.protocols import CacheBackendProtocol
    from lexigram.cache.service.stampede import StampedeProtectedCache

_T = TypeVar("_T")


logger = get_logger(__name__)

_BACKEND_ERRORS = (
    RuntimeError,
    OSError,
    ConnectionError,
    ValueError,
    TypeError,
    AttributeError,
    KeyError,
)


@inject
class CacheService(PipelineMixin, InvalidationMixin, PatternsMixin):
    """High-level cache service with advanced features.

    Provides a unified interface for caching operations across backend
    implementations (memory, Redis, Memcached).  Stampede protection,
    metrics tracking, tag-based invalidation, and batch operations are
    composed in via mixin inheritance.

    Attributes:
        provider: The cache backend provider.
        config: Configuration for cache operations.
    """

    def __init__(
        self,
        provider: CacheProvider | None = None,
        config: CacheOperationConfig | None = None,
        protection: StampedeProtectedCache | None = None,
        backend: CacheBackendProtocol | None = None,
        ctx: Context | None = None,
        max_tags: int = 10_000,
    ):
        """
        Initialize the cache service.

        Args:
            provider: Cache provider for backend management (optional)
            config: Service-level configuration
            protection: Cache stampede protection instance
            backend: Direct backend instance (optional, for standalone usage)
            ctx: Optional context for request-scoped cache keys
            max_tags: Maximum number of tags tracked in the in-memory index.
                When the cap is reached, the oldest tag (by insertion/access
                order) is evicted.  Defaults to 10 000.
        """
        self.provider = provider
        self._backend = backend
        self.config = config or default_cache_config()
        self._protection = protection
        self._ctx = ctx

        # Performance metrics
        self._metrics = {"hits": 0, "misses": 0, "errors": 0, "operations": 0}
        # Lock to make metrics updates thread-safe
        self._metrics_lock = asyncio.Lock()
        # In-memory tag → key index for tag-based invalidation.
        # OrderedDict preserves insertion/access order so the LRU eviction in
        # InvalidationMixin.set_with_tags can cheaply pop the oldest entry.
        self._tag_index: OrderedDict[str, set[str]] = OrderedDict()
        self._max_tags: int = max_tags

    def _get_backend(self, name: str | None = None) -> CacheBackendProtocol:
        """Resolve backend from direct injection or provider."""
        if self._backend is not None:
            return self._backend
        if self.provider is not None:
            return cast("CacheBackendProtocol", self.provider.get_backend(name))
        raise RuntimeError(
            "No backend or provider available for CacheService. "
            "Initialize with either a provider or a direct backend.",
        )

    async def close(self) -> None:
        """Close the cache service, releasing any background resources."""
        try:
            if self._protection and hasattr(self._protection, "close"):
                if asyncio.iscoroutinefunction(self._protection.close):
                    await self._protection.close()
                else:
                    self._protection.close()
        except Exception as e:
            logger.error("cache_close_failed", error=str(e), exc_info=True)
        finally:
            self._protection = None

    def _get_namespaced_key(self, key: str, request_scoped: bool = False) -> str:
        """
        Get a namespaced key with optional request scoping.

        Args:
            key: Original cache key
            request_scoped: If True, scope to current request (rarely needed)

        Returns:
            Namespaced key
        """
        if request_scoped:
            request_id = self._ctx.get(REQUEST_ID) if self._ctx is not None else None
            if request_id:
                return f"req:{request_id}:{key}"
        return key

    def _add_ttl_jitter(self, ttl: int | None) -> int | None:
        """
        Add jitter to TTL to prevent cache stampede.

        Applies ±10% jitter to the TTL to spread out expiration times
        and prevent thundering herd problems.

        Args:
            ttl: Original TTL in seconds

        Returns:
            TTL with jitter applied, or None if ttl was None
        """
        if ttl is None:
            return None

        # Apply ±10% jitter
        jitter_percent = 0.1
        jitter = int(ttl * jitter_percent)
        actual_ttl = ttl + random.randint(-jitter, jitter)

        # Ensure TTL is at least 1 second
        return max(1, actual_ttl)

    async def get(
        self,
        key: str,
        backend: str | None = None,
        default: Any = None,
        request_scoped: bool = False,
    ) -> Any:
        """
        Get a value from cache with error handling.

        Args:
            key: Cache key
            backend: Backend name (uses default if None)
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        try:
            namespaced_key = self._get_namespaced_key(key, request_scoped)
            backend_instance = self._get_backend(backend)
            value = cast("Any", await backend_instance.get(namespaced_key))

            # Backend implementations (e.g. RedisCacheBackend) return
            # Result[T | None, CacheError] rather than a raw value.
            # Unwrap so consumers always receive the plain Python value.
            if hasattr(value, "is_ok"):
                if value.is_ok():
                    value = value.unwrap()
                else:
                    # Backend signalled an error via Result — treat as miss.
                    async with self._metrics_lock:
                        self._metrics["errors"] += 1
                    return default

            if value is not None:
                async with self._metrics_lock:
                    self._metrics["hits"] += 1
                return value
            async with self._metrics_lock:
                self._metrics["misses"] += 1
            return default

        except _BACKEND_ERRORS as e:
            logger.warning("Cache get failed for key '%s': %s", key, e)
            async with self._metrics_lock:
                self._metrics["errors"] += 1
            return default

        finally:
            async with self._metrics_lock:
                self._metrics["operations"] += 1

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        backend: str | None = None,
    ) -> bool:
        """
        Set a value in cache with error handling.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            backend: Backend name (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        try:
            namespaced_key = self._get_namespaced_key(key)
            backend_instance = self._get_backend(backend)

            # Add jitter to TTL to prevent cache stampede
            actual_ttl = self._add_ttl_jitter(ttl)

            # Fast path: primitives are stored directly without serialization.
            # The backend receives a plain Python scalar; no pickle/JSON round-trip
            # is needed and the value can be returned as-is on cache hit.
            if isinstance(value, (str, int, float, bool)):
                success = await backend_instance.set(namespaced_key, value, actual_ttl)
                return bool(success)

            success = await backend_instance.set(namespaced_key, value, actual_ttl)
            return bool(success)

        except _BACKEND_ERRORS as e:
            logger.warning("Cache set failed for key '%s': %s", key, e)
            async with self._metrics_lock:
                self._metrics["errors"] += 1
            return False

        finally:
            async with self._metrics_lock:
                self._metrics["operations"] += 1

    async def delete(self, key: str, backend: str | None = None) -> bool:
        """
        Delete a value from cache.

        Args:
            key: Cache key
            backend: Backend name (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        try:
            namespaced_key = self._get_namespaced_key(key)
            backend_instance = self._get_backend(backend)
            return bool(await backend_instance.delete(namespaced_key))

        except _BACKEND_ERRORS as e:
            logger.warning("Cache delete failed for key '%s': %s", key, e)
            async with self._metrics_lock:
                self._metrics["errors"] += 1
            return False

        finally:
            async with self._metrics_lock:
                self._metrics["operations"] += 1

    async def delete_pattern(self, pattern: str, backend: str | None = None) -> int:
        """Delete all keys matching a glob-style pattern.

        Delegates to the backend's ``delete_pattern`` implementation.
        Redis uses SCAN + DEL; Memory iterates its in-process store.
        The namespace prefix (if any) is applied by the backend itself.

        Args:
            pattern: Glob pattern, e.g. ``"pet:list:*"``.
            backend: Named backend to use (uses default if ``None``).

        Returns:
            Number of keys deleted, or 0 on error.
        """
        try:
            backend_instance = self._get_backend(backend)
            result = await backend_instance.delete_pattern(pattern)
            count = (
                result.unwrap_or(0)
                if hasattr(result, "unwrap_or")
                else int(bool(result))
            )
            async with self._metrics_lock:
                self._metrics["operations"] += 1
            return count
        except _BACKEND_ERRORS as e:
            logger.warning("Cache delete_pattern failed for '%s': %s", pattern, e)
            async with self._metrics_lock:
                self._metrics["errors"] += 1
            return 0

    async def exists(self, key: str, backend: str | None = None) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key
            backend: Backend name (uses default if None)

        Returns:
            True if key exists, False otherwise
        """
        try:
            namespaced_key = self._get_namespaced_key(key)
            backend_instance = self._get_backend(backend)
            return bool(await backend_instance.exists(namespaced_key))

        except _BACKEND_ERRORS as e:
            logger.warning("Cache exists check failed for key '%s': %s", key, e)
            async with self._metrics_lock:
                self._metrics["errors"] += 1
            return False

        finally:
            async with self._metrics_lock:
                self._metrics["operations"] += 1

    async def clear(self, backend: str | None = None) -> bool:
        """
        Clear all values from cache.

        Args:
            backend: Backend name (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        try:
            backend_instance = self._get_backend(backend)
            return bool(await backend_instance.clear())

        except _BACKEND_ERRORS as e:
            logger.warning("Cache clear failed: %s", e)
            self._metrics["errors"] += 1
            return False

        finally:
            self._metrics["operations"] += 1

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """
        Get comprehensive health status of the cache service.

        Returns:
            Structured health check result.
        """
        if self.provider:
            provider_health = await self.provider.health_check()

            # Handle both dict and HealthCheckResult
            if hasattr(provider_health, "status"):
                status: HealthStatus = provider_health.status
                backends_detail = getattr(provider_health, "details", {}).get(
                    "backends",
                    {},
                )
                error = getattr(provider_health, "error", None)
            elif isinstance(provider_health, dict):
                status = provider_health.get("status", "unknown")
                backends_detail = provider_health.get("details", {}).get("backends", {})
                error = provider_health.get("error")
            else:
                status = HealthStatus.UNHEALTHY
                backends_detail = {}
                error = "Invalid health check result"
        else:
            # Standalone mode: assume healthy if operations are working
            status = HealthStatus.HEALTHY
            error = None
            backends_detail = {"standalone": "healthy"}

        return HealthCheckResult(
            component="cache:service",
            status=status,
            details={
                "backends": backends_detail,
                "service": {
                    "operations": self._metrics["operations"],
                    "hits": self._metrics["hits"],
                    "misses": self._metrics["misses"],
                    "errors": self._metrics["errors"],
                    "hit_rate": (
                        self._metrics["hits"] / max(self._metrics["operations"], 1)
                    ),
                    "protection_enabled": self._protection is not None,
                },
            },
            error=error,
        )

    def get_metrics(self) -> dict[str, int]:
        """
        Get service performance metrics.

        Returns:
            Dictionary of metrics
        """
        return self._metrics.copy()

    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self._metrics = {"hits": 0, "misses": 0, "errors": 0, "operations": 0}

    async def get_typed(
        self,
        key: str,
        type_: type[_T],
        backend: str | None = None,
        default: _T | None = None,
    ) -> _T | None:
        """Get a value from cache and cast it to the requested type.

        Unlike :meth:`get`, which returns :class:`Any`, this method provides
        compile-time type safety.  The stored value is returned as-is if it
        is already an instance of *type_*; otherwise the raw value is passed
        to ``type_(**raw)`` (for dict-like values) or ``type_(raw)`` as a
        fallback.

        Args:
            key: Cache key.
            type_: The expected Python type of the cached value.
            backend: Backend name (uses default if ``None``).
            default: Value returned when the key is absent or deserialisation
                fails.

        Returns:
            The cached value cast to *type_*, or *default*.
        """
        raw = await self.get(key, backend=backend)
        if raw is None:
            return default
        if isinstance(raw, type_):
            return raw
        try:
            if isinstance(raw, dict):
                return type_(**raw)
            return type_(raw)  # type: ignore[call-arg]
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Cache get_typed: cannot coerce value for key %r to %s: %s",
                key,
                type_.__name__,
                exc,
            )
            return default
