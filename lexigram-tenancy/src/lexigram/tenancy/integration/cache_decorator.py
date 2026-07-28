"""Cache key decorator that prefixes keys with the current tenant ID."""

from __future__ import annotations

from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.primitives.context import TENANT_ID, Context


class TenantCacheKeyDecorator:
    """Wraps a cache backend to automatically prefix keys with ``t:{tenant_id}:``.

    When no tenant is in context the original key is used unchanged,
    so the decorator is safe for non-tenant-scoped cache operations.

    This class duck-types ``CacheBackendProtocol`` so it can be substituted
    for any cache backend implementation.

    Usage::

        from lexigram.contracts.infra.cache import CacheBackendProtocol

        decorator = TenantCacheKeyDecorator(inner=redis_backend, ctx=context)
        # Use as a drop-in replacement for redis_backend
        await decorator.set("my_key", b"value", ttl=60)
    """

    def __init__(self, inner: CacheBackendProtocol, ctx: Context) -> None:
        """Initialise the decorator.

        Args:
            inner: The underlying cache backend (duck-typed
                :class:`~lexigram.contracts.infra.cache.CacheBackendProtocol`).
            ctx: Shared :class:`~lexigram.primitives.context.Context` used to
                read the current ``TENANT_ID``.
        """
        self._inner = inner
        self._ctx = ctx

    def _prefixed_key(self, key: str) -> str:
        """Compute the tenant-prefixed cache key.

        Args:
            key: Original cache key.

        Returns:
            ``t:{tenant_id}:{key}`` when a tenant is in context,
            otherwise the original *key*.
        """
        tenant_id = self._ctx.get(TENANT_ID)
        if tenant_id:
            return f"t:{tenant_id}:{key}"
        return key

    async def get(self, key: str) -> bytes | None:
        """Retrieve a value by its (prefixed) key.

        Args:
            key: Cache key (will be prefixed if a tenant is active).

        Returns:
            Cached bytes, or ``None`` if not found.
        """
        return await self._inner.get(self._prefixed_key(key))  # type: ignore[return-value]

    async def set(self, key: str, value: bytes, ttl: int | None = None) -> None:
        """Store a value under the (prefixed) key.

        Args:
            key: Cache key (will be prefixed if a tenant is active).
            value: Bytes to store.
            ttl: Optional TTL in seconds.
        """
        await self._inner.set(self._prefixed_key(key), value, ttl)

    async def delete(self, key: str) -> None:
        """Delete the value at the (prefixed) key.

        Args:
            key: Cache key (will be prefixed if a tenant is active).
        """
        await self._inner.delete(self._prefixed_key(key))

    async def exists(self, key: str) -> bool:
        """Check if a key exists (prefixed).

        Args:
            key: Cache key (will be prefixed if a tenant is active).

        Returns:
            ``True`` if the key exists.
        """
        return await self._inner.exists(self._prefixed_key(key))  # type: ignore[return-value]


__all__ = ["TenantCacheKeyDecorator"]
