"""TTL-based caching wrapper for TenantConfigProviderProtocol."""

from __future__ import annotations

import time
from typing import Any

from lexigram.contracts.tenancy.protocols import TenantConfigProviderProtocol


class CachedTenantConfigProvider:
    """Decorator that wraps any :class:`~lexigram.contracts.tenancy.protocols.TenantConfigProviderProtocol`
    with in-process TTL caching.

    The entire config dict for a tenant is cached as a unit.  A write
    (``set_config``) invalidates the cached dict for that tenant so the
    next read fetches fresh data.

    Usage::

        base_provider = InMemoryTenantProvider()
        cached = CachedTenantConfigProvider(base_provider, ttl=60)
        value = await cached.get_config("tenant-abc", "feature_x")
    """

    def __init__(
        self,
        inner: TenantConfigProviderProtocol,
        ttl: int = 60,
    ) -> None:
        """Initialise the caching decorator.

        Args:
            inner: The underlying config provider to wrap.
            ttl: Cache TTL in seconds.
        """
        self._inner = inner
        self._ttl = ttl
        self._cache: dict[str, tuple[dict[str, Any], float]] = {}

    async def get_config(self, tenant_id: str, key: str) -> Any | None:
        """Get a single config value, using the tenant-level cache.

        Args:
            tenant_id: The tenant whose config is queried.
            key: Configuration key.

        Returns:
            The value if set, or ``None``.
        """
        all_config = await self.get_all_config(tenant_id)
        return all_config.get(key)

    async def get_all_config(self, tenant_id: str) -> dict[str, Any]:
        """Get all config for a tenant, from cache if valid.

        Args:
            tenant_id: The tenant whose config is retrieved.

        Returns:
            Dictionary of all key-value pairs for the tenant.
        """
        cached = self._cache.get(tenant_id)
        if cached is not None:
            config, ts = cached
            if (time.monotonic() - ts) < self._ttl:
                return config
        config = await self._inner.get_all_config(tenant_id)
        self._cache[tenant_id] = (config, time.monotonic())
        return config

    async def set_config(self, tenant_id: str, key: str, value: Any) -> None:
        """Set a config value and invalidate the cache.

        Args:
            tenant_id: The tenant whose config is updated.
            key: Configuration key.
            value: New value (must be JSON-serialisable).
        """
        await self._inner.set_config(tenant_id, key, value)
        self._cache.pop(tenant_id, None)


__all__ = ["CachedTenantConfigProvider"]
