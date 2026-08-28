"""Caching Utilities for Search Operations"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from lexigram import hashing as ambient_hashing
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.search.exceptions import CacheError
from lexigram.search.types import SearchResponse
from lexigram.serialization import dumps, loads

logger = get_logger(__name__)


@dataclass
class CacheConfig:
    """Cache configuration"""

    ttl_seconds: int = 300  # 5 minutes
    max_size: int = 1000
    cleanup_interval: int = 60  # 1 minute
    enable_compression: bool = False
    serializer: Literal["json"] = "json"  # json only; pickle removed for security


@dataclass
class CacheEntry:
    """Cache entry"""

    key: str
    value: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = 0
    ttl_seconds: int | None = None

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl_seconds is None:
            return False

        expires_at = self.created_at + timedelta(seconds=self.ttl_seconds)
        return ambient_clock.now() > expires_at

    @property
    def age_seconds(self) -> float:
        """Get entry age in seconds"""
        return (ambient_clock.now() - self.created_at).total_seconds()


class SearchCache:
    """Cache for search operations"""

    def __init__(self, config: CacheConfig | None = None):
        self.config = config or CacheConfig()
        self._cache: dict[str, CacheEntry] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start cache maintenance"""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop cache maintenance"""
        if not self._running:
            return

        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._cleanup_task

    def generate_key(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        sort: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate cache key from search parameters"""
        # Create a deterministic representation
        key_data = {
            "query": query,
            "filters": filters or {},
            "sort": sort or [],
            "kwargs": {
                k: v for k, v in kwargs.items() if k not in ["limit", "offset"]
            },  # Exclude pagination
        }

        # Sort for consistency
        key_string = dumps(key_data, sort_keys=True, default=str)

        # Hash for fixed length (dumps returns bytes in our json helper)
        return cast("str", ambient_hashing.digest(key_string))

    async def get(self, key: str) -> Any | None:
        """Get value from cache"""
        entry = self._cache.get(key)

        if entry is None:
            return None

        if entry.is_expired:
            await self.delete(key)
            return None

        # Update access statistics
        entry.accessed_at = datetime.now(UTC)
        entry.access_count += 1

        # Deserialize value
        return await self._deserialize(entry.value)

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Set value in cache"""
        # Check cache size limit
        if len(self._cache) >= self.config.max_size:
            await self._evict_entries()

        # Serialize value
        serialized_value = await self._serialize(value)

        # Create entry
        entry = CacheEntry(
            key=key,
            value=serialized_value,
            ttl_seconds=ttl_seconds or self.config.ttl_seconds,
        )

        self._cache[key] = entry

    async def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self._cache)
        total_accesses = sum(entry.access_count for entry in self._cache.values())
        avg_age = (
            sum(entry.age_seconds for entry in self._cache.values()) / total_entries
            if total_entries > 0
            else 0
        )

        return {
            "total_entries": total_entries,
            "max_size": self.config.max_size,
            "total_accesses": total_accesses,
            "average_age_seconds": avg_age,
            "hit_rate": total_accesses
            / max(
                total_accesses
                + (
                    total_entries
                    - len(
                        list(
                            filter(lambda e: e.access_count == 0, self._cache.values()),
                        ),
                    )
                ),
                1,
            ),
        }

    async def _serialize(self, value: Any) -> str | bytes:
        """Serialize value for storage."""
        if self.config.serializer != "json":
            raise CacheError(f"Unsupported serializer: {self.config.serializer}")
        return dumps(value, default=str)

    async def _deserialize(self, value: str) -> Any:
        """Deserialize value from storage."""
        if self.config.serializer != "json":
            raise CacheError(f"Unsupported serializer: {self.config.serializer}")
        return loads(value)

    async def _evict_entries(self) -> None:
        """Evict entries using LRU strategy"""
        if not self._cache:
            return

        # Sort by access time (oldest first)
        entries = sorted(self._cache.items(), key=lambda x: x[1].accessed_at)

        # Remove oldest 10% or at least 1 entry
        to_remove = max(1, len(entries) // 10)

        for key, _ in entries[:to_remove]:
            del self._cache[key]

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of expired entries"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except (OSError, RuntimeError, ValueError) as e:
                logger.debug("Cache cleanup error: %s", e)
                continue

    async def _cleanup_expired(self) -> None:
        """Remove expired entries"""
        expired_keys = [
            kv[0] for kv in filter(lambda kv: kv[1].is_expired, self._cache.items())
        ]

        for key in expired_keys:
            del self._cache[key]


class QueryCache:
    """Cache specifically for search queries"""

    def __init__(self, cache: SearchCache):
        self.cache = cache

    async def get_search_results(
        self,
        query: str,
        **search_params: Any,
    ) -> SearchResponse | None:
        """Get cached search results"""
        key = self.cache.generate_key(query, **search_params)
        return await self.cache.get(key)

    async def set_search_results(
        self,
        query: str,
        results: SearchResponse,
        **search_params: Any,
    ) -> None:
        """Cache search results"""
        key = self.cache.generate_key(query, **search_params)
        await self.cache.set(key, results)

    async def invalidate_query(self, query: str, **search_params: Any) -> None:
        """Invalidate cached query results"""
        key = self.cache.generate_key(query, **search_params)
        await self.cache.delete(key)

    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        import re

        pattern_regex = re.compile(pattern)
        invalidated = 0

        keys_to_delete = [key for key in self.cache._cache if pattern_regex.match(key)]

        for key in keys_to_delete:
            if await self.cache.delete(key):
                invalidated += 1

        return invalidated


class CacheManager:
    """Manages multiple caches"""

    def __init__(self) -> None:
        self.caches: dict[str, SearchCache] = {}
        self.query_caches: dict[str, QueryCache] = {}

    def create_cache(self, name: str, config: CacheConfig | None = None) -> SearchCache:
        """Create a new cache"""
        if name in self.caches:
            raise CacheError(f"Cache '{name}' already exists")

        cache = SearchCache(config)
        self.caches[name] = cache
        self.query_caches[name] = QueryCache(cache)

        return cache

    def get_cache(self, name: str) -> SearchCache:
        """Get cache by name"""
        if name not in self.caches:
            raise CacheError(f"Cache '{name}' not found")
        return self.caches[name]

    def get_query_cache(self, name: str) -> QueryCache:
        """Get query cache by name"""
        if name not in self.query_caches:
            raise CacheError(f"Query cache '{name}' not found")
        return self.query_caches[name]

    async def start_all(self) -> None:
        """Start all caches"""
        for cache in self.caches.values():
            await cache.start()

    async def stop_all(self) -> None:
        """Stop all caches"""
        for cache in self.caches.values():
            await cache.stop()

    async def clear_all(self) -> None:
        """Clear all caches"""
        for cache in self.caches.values():
            await cache.clear()


@asynccontextmanager
async def cache_context(cache: SearchCache) -> Any:
    """Context manager for cache operations"""
    try:
        await cache.start()
        yield cache
    finally:
        await cache.stop()


# Cache decorators
def cached(cache: SearchCache, ttl_seconds: int | None = None) -> Any:
    """Decorator to cache function results"""

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key from function call
            key_data = {"func": func.__name__, "args": args, "kwargs": kwargs}
            key = ambient_hashing.digest(
                dumps(key_data, sort_keys=True, default=str),
            )

            # Try to get from cache
            cached_result = await cache.get(key)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache.set(key, result, ttl_seconds)

            return result

        return wrapper

    return decorator


__all__ = [
    "CacheConfig",
    "CacheEntry",
    "CacheManager",
    "QueryCache",
    "SearchCache",
    "cache_context",
    "cached",
]
