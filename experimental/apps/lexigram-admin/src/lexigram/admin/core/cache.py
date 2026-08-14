"""Cache integration for lexigram-admin.

Provides ``AdminCacheService`` — a thin, Result-unwrapping facade over
``CacheBackendProtocol`` — and ``CachedPermissionService``, which layers a
process-local L1 cache in front of an optional distributed backend.

Cross-request caching decorators (``@cache``, ``@remember``,
``@invalidate_cache``) live in ``lexigram.cache.service.decorators``.
Request-scoped caching lives in ``lexigram.cache.service.request_cache``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
from typing import Any, Protocol, runtime_checkable

from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.di.decorators import inject
from lexigram.serialization import dumps_str

# ============================================================================
# Cache Key Builders
# ============================================================================


def default_key_builder(func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:  # type: ignore[name-defined]
    """Build cache key from function and arguments."""
    # Get function identifier
    func_name = f"{func.__module__}.{func.__qualname__}"

    # Serialize arguments
    key_parts = [func_name]

    for arg in args:
        if hasattr(arg, "id"):
            key_parts.append(f"id:{arg.id}")
        elif isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(hashlib.sha256(dumps_str(arg).encode()).hexdigest()[:8])

    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}:{v}")
        else:
            key_parts.append(
                f"{k}:{hashlib.sha256(dumps_str(v).encode()).hexdigest()[:8]}",
            )

    return ":".join(key_parts)


# ============================================================================
# Cache Service
# ============================================================================


@inject
class AdminCacheService:
    """Core caching service for the admin panel.

    Provides a clean, unified API for caching using a
    contract-based cache backend.

    Example:
        >>> cache = AdminCacheService(cache_backend=my_backend)
        >>> await cache.set("user:1", {"name": "Admin"})
        >>> user = await cache.get("user:1")
    """

    def __init__(
        self,
        cache_backend: CacheBackendProtocol,
    ) -> None:
        """Initialize the service.

        Args:
            cache_backend: Cache backend to use for storage
        """
        self._backend = cache_backend

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        res = await self._backend.get(key)
        return res.unwrap() if res.is_ok() else None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache."""
        res = await self._backend.set(key, value, ttl)
        return res.is_ok()

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        res = await self._backend.delete(key)
        return res.unwrap() if res.is_ok() else False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        res = await self._backend.delete_pattern(pattern)
        return res.unwrap() if res.is_ok() else 0

    async def get_or_set(
        self,
        key: str,
        factory: Any,
        ttl: int | None = None,
    ) -> Any:
        """Get from cache or compute and store."""
        value = await self.get(key)
        if value is not None:
            return value

        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        await self.set(key, value, ttl)
        return value


# ============================================================================
# Cached Permission Service
# ============================================================================


@runtime_checkable
class UserRoleProviderProtocol(Protocol):
    """Protocol for user role providers."""

    async def get_roles(self, user: Any) -> list[str]: ...

    async def get_role_permissions(self, role: str) -> set[str]: ...


@inject
class CachedPermissionService:
    """Permission service with caching.

    Caches user permissions with configurable TTL.

    Example:
        >>> service = CachedPermissionService(role_provider, ttl=300)
        >>> permissions = await service.get_permissions(user)
    """

    def __init__(
        self,
        role_provider: UserRoleProviderProtocol,
        cache_backend: CacheBackendProtocol | None = None,
        ttl: int = 300,
    ):
        self._role_provider = role_provider
        self._cache: CacheBackendProtocol | None = cache_backend
        self._ttl = ttl
        self._local_cache: dict[Any, tuple[set[str], datetime]] = {}

    async def get_permissions(self, user: Any) -> set[str]:
        """Get user permissions with caching."""
        user_id = getattr(user, "id", id(user))
        cache_key = f"admin:perms:{user_id}"

        # Check local cache first (process-level)
        if user_id in self._local_cache:
            perms, expires = self._local_cache[user_id]
            if datetime.now(UTC) < expires:
                return perms
            del self._local_cache[user_id]

        # Check distributed cache
        if self._cache is not None:
            res = await self._cache.get(cache_key)
            if res.is_ok():
                cached = res.unwrap()
                if cached is not None:
                    self._local_cache[user_id] = (
                        cached,
                        datetime.now(UTC) + timedelta(seconds=self._ttl // 2),
                    )
                    return cached

        # Compute permissions
        permissions: set[str] = set()
        roles = await self._role_provider.get_roles(user)

        for role in roles:
            role_permissions = await self._role_provider.get_role_permissions(role)
            permissions.update(role_permissions)

        # Cache permissions
        if self._cache is not None:
            await self._cache.set(cache_key, permissions, self._ttl)
        self._local_cache[user_id] = (
            permissions,
            datetime.now(UTC) + timedelta(seconds=self._ttl // 2),
        )

        return permissions

    async def invalidate_user(self, user_id: Any) -> None:
        """Invalidate cached permissions for a user."""
        cache_key = f"admin:perms:{user_id}"
        if self._cache is not None:
            await self._cache.delete(cache_key)
        self._local_cache.pop(user_id, None)

    async def invalidate_all(self) -> None:
        """Invalidate all cached permissions."""
        if self._cache is not None:
            await self._cache.delete_pattern("admin:perms:*")
        self._local_cache.clear()

    def has_permission(self, user: Any, permission: str) -> bool:
        """Check if user has permission (sync, uses local cache)."""
        user_id = getattr(user, "id", id(user))
        if user_id in self._local_cache:
            perms, expires = self._local_cache[user_id]
            if datetime.now(UTC) < expires:
                return permission in perms
        return False


__all__ = [
    # Service
    "AdminCacheService",
    # Backend protocol re-export for ergonomic imports
    "CacheBackendProtocol",
    # Permission caching
    "CachedPermissionService",
    "UserRoleProviderProtocol",
    # Key builders
    "default_key_builder",
]
