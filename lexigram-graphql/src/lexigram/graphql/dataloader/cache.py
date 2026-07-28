"""DataLoaderProtocol cache implementations.

This module provides cache implementations for DataLoaderProtocol,
including in-memory caching with TTL support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Hashable
from dataclasses import dataclass
import time
from typing import Generic, TypeVar

from lexigram.logging import get_logger

logger = get_logger(__name__)

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LoaderCache(ABC, Generic[K, V]):
    """Abstract base class for DataLoaderProtocol caches.

    Implement this interface to provide custom caching
    behavior for DataLoaders.
    """

    @abstractmethod
    def get(self, key: K) -> V | None:
        """Get a cached value.

        Args:
            key: Cache key.

        Returns:
            Cached value or None.
        """
        ...

    @abstractmethod
    def set(self, key: K, value: V) -> None:
        """Set a cached value.

        Args:
            key: Cache key.
            value: Value to cache.
        """
        ...

    @abstractmethod
    def has(self, key: K) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key.

        Returns:
            True if key exists.
        """
        ...

    @abstractmethod
    def delete(self, key: K) -> None:
        """Delete a cached value.

        Args:
            key: Cache key.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        ...


@dataclass
class LoaderCacheEntry(Generic[V]):
    """Cache entry with expiration support.

    Attributes:
        value: Cached value.
        expires_at: Expiration timestamp (or 0 for no expiry).
    """

    value: V
    expires_at: float = 0

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at <= 0:
            return False
        return time.time() > self.expires_at


class InMemoryCache(LoaderCache[K, V]):
    """In-memory cache implementation.

    Simple in-memory cache with optional TTL support.
    Suitable for single-request caching in DataLoaders.

    Example:
        ```python
        cache = InMemoryCache[str, User](ttl_seconds=60)

        cache.set("user:1", user)
        user = cache.get("user:1")
        ```
    """

    def __init__(
        self,
        ttl_seconds: float = 0,
        max_size: int = 0,
    ) -> None:
        """Initialize the cache.

        Args:
            ttl_seconds: Time-to-live in seconds (0 for no TTL).
            max_size: Maximum cache size (0 for unlimited).
        """
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        self._cache: dict[K, LoaderCacheEntry[V]] = {}

    @property
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    def get(self, key: K) -> V | None:
        """Get a cached value.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found or expired.
        """
        entry = self._cache.get(key)

        if entry is None:
            return None

        if entry.is_expired():
            del self._cache[key]
            return None

        return entry.value

    def set(self, key: K, value: V) -> None:
        """Set a cached value.

        Args:
            key: Cache key.
            value: Value to cache.
        """
        # Check max size
        if self._max_size > 0 and len(self._cache) >= self._max_size and self._cache:
            # Remove oldest entry (FIFO eviction)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        # Calculate expiration
        expires_at = 0.0
        if self._ttl_seconds > 0:
            expires_at = time.time() + self._ttl_seconds

        self._cache[key] = LoaderCacheEntry(value=value, expires_at=expires_at)

    def has(self, key: K) -> bool:
        """Check if key exists and is not expired.

        Args:
            key: Cache key.

        Returns:
            True if key exists and is valid.
        """
        entry = self._cache.get(key)

        if entry is None:
            return False

        if entry.is_expired():
            del self._cache[key]
            return False

        return True

    def delete(self, key: K) -> None:
        """Delete a cached value.

        Args:
            key: Cache key.
        """
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries.

        Returns:
            Number of entries removed.
        """
        expired_keys = [
            kv[0] for kv in filter(lambda kv: kv[1].is_expired(), self._cache.items())
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)


class NoOpCache(LoaderCache[K, V]):
    """No-operation cache (disables caching).

    Use this when you want to disable DataLoaderProtocol caching
    while keeping the batching behavior.
    """

    def get(self, key: K) -> V | None:
        """Always returns None."""
        return None

    def set(self, key: K, value: V) -> None:
        """Does nothing."""

    def has(self, key: K) -> bool:
        """Always returns False."""
        return False

    def delete(self, key: K) -> None:
        """Does nothing."""

    def clear(self) -> None:
        """Does nothing."""


__all__ = ["InMemoryCache", "LoaderCache", "LoaderCacheEntry", "NoOpCache"]
