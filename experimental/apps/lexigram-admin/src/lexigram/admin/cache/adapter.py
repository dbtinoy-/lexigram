"""Adapter that delegates admin caching to ``lexigram-cache``.

When ``lexigram-cache`` is installed, ``AdminCacheServiceAdapter`` wraps
``lexigram.cache.service.core.CacheService`` for rich caching features
(stampede protection, tag invalidation, batch ops).  When not installed,
it falls back to a no-op that satisfies the same protocol.
"""

from __future__ import annotations

from typing import Any

try:
    from lexigram.cache.service.core import CacheService as _LexigramCacheService
    from lexigram.contracts.infra.cache import CacheBackendProtocol

    _HAS_CACHE = True
except ImportError:  # noqa: F841
    _HAS_CACHE = False
    _LexigramCacheService = object  # type: ignore[assignment,misc]
    CacheBackendProtocol = object  # type: ignore[assignment,misc]


class AdminCacheServiceAdapter:
    """Bridge between admin's cache needs and ``lexigram-cache``'s ``CacheService``.

    Usage::

        adapter = AdminCacheServiceAdapter(cache_service=real_service)
        value = await adapter.get("key")
        await adapter.set("key", value, ttl=60)
    """

    def __init__(
        self,
        cache_service: Any | None = None,
    ) -> None:
        self._service = cache_service

    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        if self._service is None:
            return None
        try:
            return await self._service.get(key)
        except Exception:  # noqa: BLE001
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a value in cache."""
        if self._service is None:
            return False
        try:
            await self._service.set(key, value, ttl)
            return True
        except Exception:  # noqa: BLE001
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if self._service is None:
            return False
        try:
            await self._service.delete(key)
            return True
        except Exception:  # noqa: BLE001
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        if self._service is None:
            return 0
        try:
            return await self._service.delete_pattern(pattern)
        except Exception:  # noqa: BLE001
            return 0

    async def get_or_set(
        self,
        key: str,
        factory: Any,
        ttl: int | None = None,
    ) -> Any:
        """Get from cache or compute and store."""
        if self._service is None:
            return await factory() if callable(factory) else factory
        try:
            return await self._service.get_or_set(key, factory, ttl)
        except Exception:  # noqa: BLE001
            return await factory() if callable(factory) else factory

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        if self._service is None:
            return False
        try:
            return await self._service.exists(key)
        except Exception:  # noqa: BLE001
            return False

    async def clear(self) -> bool:
        """Clear all cached entries."""
        if self._service is None:
            return False
        try:
            await self._service.clear()
            return True
        except Exception:  # noqa: BLE001
            return False


__all__ = ["AdminCacheServiceAdapter"]
