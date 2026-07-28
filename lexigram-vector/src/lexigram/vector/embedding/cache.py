"""Embedding cache layer for vector operations.

This module provides caching for expensive embedding operations using lexigram-cache.
"""

from __future__ import annotations

import hashlib
from typing import Any

from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.logging import get_logger
from lexigram.result import Result
from lexigram.vector.types import Embedding

logger = get_logger(__name__)


class EmbeddingCache:
    """Cache layer for embedding operations.

    Caches embedding vectors to avoid recomputing expensive operations.
    Integrates with lexigram-cache for distributed caching support.

    Example:
        >>> from lexigram.vector.embedding.cache import EmbeddingCache
        >>>
        >>> cache = EmbeddingCache(cache_service=cache_service)
        >>>
        >>> # Try to get from cache
        >>> embedding = await cache.get("My text to embed")
        >>> if embedding is None:
        ...     # Cache miss - compute embedding
        ...     embedding = await embedding_model.embed("My text to embed")
        ...     await cache.set("My text to embed", embedding)
    """

    def __init__(
        self,
        cache_service: CacheBackendProtocol | None,
        ttl: int = 86400,  # 24 hours default
        key_prefix: str = "embedding:",
        enabled: bool = True,
    ):
        """Initialize embedding cache.

        Args:
            cache_service: Cache backend implementing CacheBackendProtocol protocol
            ttl: Time-to-live for cache entries in seconds
            key_prefix: Prefix for cache keys
            enabled: Whether caching is enabled
        """
        self.cache_service = cache_service
        self.ttl = ttl
        self.key_prefix = key_prefix
        self.enabled = enabled if cache_service is not None else False

    def _generate_key(self, text: str, model: str | None = None) -> str:
        """Generate cache key for text and model.

        Args:
            text: Text to embed
            model: Optional model name to include in key

        Returns:
            Cache key string
        """
        # Use hash of text to keep keys manageable
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

        if model:
            return f"{self.key_prefix}{model}:{text_hash}"
        return f"{self.key_prefix}{text_hash}"

    async def get(
        self,
        text: str,
        model: str | None = None,
    ) -> Embedding | None:
        """Get embedding from cache.

        Args:
            text: Text to get embedding for
            model: Optional model name

        Returns:
            Cached embedding vector or None if not found
        """
        if not self.enabled:
            return None

        try:
            key = self._generate_key(text, model)
            cached_result = await self.cache_service.get(key)  # type: ignore[union-attr]
        except (
            AttributeError,
            KeyError,
            TypeError,
            ConnectionError,
            OSError,
            ValueError,
        ):
            logger.exception("Error getting from embedding cache")
            return None
        else:
            if isinstance(cached_result, Result):
                if cached_result.is_err():
                    logger.warning(
                        "Embedding cache read failed",
                        key=key,
                        error=str(cached_result.unwrap_err()),
                    )
                    return None
                cached = cached_result.unwrap()
            else:
                cached = cached_result

            if cached is not None:
                logger.debug("Embedding cache hit for key: %s", key)
                return cached

            logger.debug("Embedding cache miss for key: %s", key)
            return None

    async def set(
        self,
        text: str,
        embedding: Embedding | list[float],
        model: str | None = None,
        ttl: int | None = None,
    ) -> bool:
        """Set embedding in cache.

        Args:
            text: Text that was embedded
            embedding: Embedding vector to cache (either an ``Embedding`` or ``list[float]``)
            model: Optional model name
            ttl: Optional custom TTL (uses default if not provided)

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            key = self._generate_key(text, model)
            cache_ttl = ttl if ttl is not None else self.ttl

            # Accept either an Embedding object or a raw list[float]. For
            # external cache services we preserve the original value so tests
            # and simple cache services receive the same shape they expect
            # (usually raw list[float]).
            value_to_cache = embedding

            set_result = await self.cache_service.set(  # type: ignore[union-attr]
                key,
                value_to_cache,
                ttl=cache_ttl,
            )
            if isinstance(set_result, Result) and set_result.is_err():
                logger.warning(
                    "Embedding cache write failed",
                    key=key,
                    error=str(set_result.unwrap_err()),
                )
                return False
        except (AttributeError, TypeError, ConnectionError, OSError, ValueError):
            logger.exception("Error setting embedding cache")
            return False
        else:
            logger.debug("Cached embedding for key: %s", key)
            return True

    async def delete(self, text: str, model: str | None = None) -> bool:
        """Delete embedding from cache.

        Args:
            text: Text to delete embedding for
            model: Optional model name

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            key = self._generate_key(text, model)
            delete_result = await self.cache_service.delete(key)  # type: ignore[union-attr]
            if isinstance(delete_result, Result) and delete_result.is_err():
                logger.warning(
                    "Embedding cache delete failed",
                    key=key,
                    error=str(delete_result.unwrap_err()),
                )
                return False
        except (AttributeError, TypeError, ConnectionError, OSError, ValueError):
            logger.warning("Error deleting from embedding cache")
            return False
        else:
            logger.debug("Deleted embedding cache for key: %s", key)
            return True

    async def clear(self, model: str | None = None) -> bool:
        """Clear all embeddings from cache.

        Args:
            model: If provided, only clear embeddings for this model

        Returns:
            True if cleared successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Note: This is a simplified implementation
            # In production, you'd want a more efficient way to clear by prefix
            if hasattr(self.cache_service, "clear_pattern"):
                pattern = (
                    f"{self.key_prefix}{model}:*" if model else f"{self.key_prefix}*"
                )
                await self.cache_service.clear_pattern(pattern)  # type: ignore[union-attr]
            else:
                logger.warning("Cache service does not support pattern clearing")
                return False
        except (AttributeError, TypeError, ConnectionError, OSError, ValueError):
            logger.warning("Error clearing embedding cache")
            return False
        else:
            logger.info("Cleared embedding cache with pattern: %s", pattern)
            return True

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled:
            return {
                "enabled": False,
                "message": "Caching disabled",
            }

        try:
            if hasattr(self.cache_service, "get_stats"):
                stats = await self.cache_service.get_stats()  # type: ignore[union-attr]
                return {
                    "enabled": True,
                    "ttl": self.ttl,
                    "key_prefix": self.key_prefix,
                    "cache_stats": stats,
                }
            return {
                "enabled": True,
                "ttl": self.ttl,
                "key_prefix": self.key_prefix,
                "message": "Cache service does not provide stats",
            }
        except (AttributeError, TypeError, ConnectionError, OSError, ValueError):
            logger.warning("Error getting cache stats")
            return {
                "enabled": True,
                "error": "Error getting cache stats",
            }


class InMemoryEmbeddingCache:
    """Simple in-memory embedding cache for development/testing.

    This is a lightweight alternative when lexigram-cache is not available.
    Should not be used in production for distributed systems.
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl: int = 86400,
    ):
        """Initialize in-memory cache.

        Args:
            max_size: Maximum number of entries to cache
            ttl: Time-to-live (not enforced in this simple implementation)
        """
        self._cache: dict[str, Embedding] = {}
        self.max_size = max_size
        self.ttl = ttl
        self.hits = 0
        self.misses = 0

    def _generate_key(self, text: str, model: str | None = None) -> str:
        """Generate cache key."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        if model:
            return f"{model}:{text_hash}"
        return text_hash

    async def get(
        self,
        text: str,
        model: str | None = None,
    ) -> Embedding | None:
        """Get embedding from cache."""
        key = self._generate_key(text, model)

        if key in self._cache:
            self.hits += 1
            return self._cache[key]

        self.misses += 1
        return None

    async def set(
        self,
        text: str,
        embedding: Embedding,
        model: str | None = None,
        ttl: int | None = None,
    ) -> bool:
        """Set embedding in cache."""
        key = self._generate_key(text, model)

        # Simple LRU: remove oldest if at max size
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Remove first (oldest) item
            self._cache.pop(next(iter(self._cache)))

        self._cache[key] = embedding
        return True

    async def delete(self, text: str, model: str | None = None) -> bool:
        """Delete embedding from cache."""
        key = self._generate_key(text, model)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def clear(self, model: str | None = None) -> bool:
        """Clear cache."""
        if model:
            # Clear only entries for specific model
            keys_to_delete = [k for k in self._cache if k.startswith(f"{model}:")]
            for key in keys_to_delete:
                del self._cache[key]
        else:
            self._cache.clear()
        return True

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "enabled": True,
            "type": "in_memory",
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "ttl": self.ttl,
        }


__all__ = [
    "EmbeddingCache",
    "InMemoryEmbeddingCache",
]
