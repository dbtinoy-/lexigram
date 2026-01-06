"""Tenant validator with in-process TTL cache."""

from __future__ import annotations

import time

from lexigram.contracts.tenancy.protocols import TenantProviderProtocol
from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus
from lexigram.logging import get_logger

logger = get_logger(__name__)


class TenantValidator:
    """Validates a ``tenant_id`` against the tenant store with TTL caching.

    Caches the lookup result in an in-process dict.  In multi-process
    deployments the cache is process-local; the TTL bounds staleness.

    Usage::

        validator = TenantValidator(provider, cache_ttl=300)
        info = await validator.validate("tenant-abc")
        if info:
            # tenant is active
            ...
    """

    def __init__(
        self,
        provider: TenantProviderProtocol,
        cache_ttl: int = 300,
    ) -> None:
        """Initialise the validator.

        Args:
            provider: Tenant storage implementing
                :class:`~lexigram.contracts.tenancy.protocols.TenantProviderProtocol`.
            cache_ttl: Seconds to cache a validated
                :class:`~lexigram.contracts.tenancy.types.TenantInfo` record.
                Defaults to 300 seconds.
        """
        self._provider = provider
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[TenantInfo, float]] = {}

    async def validate(self, tenant_id: str) -> TenantInfo | None:
        """Validate that a tenant exists and is active.

        Results are cached for ``cache_ttl`` seconds.  Returns ``None`` for
        inactive, suspended, or provisioning tenants.

        Args:
            tenant_id: Identifier of the tenant to validate.

        Returns:
            The :class:`~lexigram.contracts.tenancy.types.TenantInfo` if the
            tenant is active, or ``None`` otherwise.
        """
        cached = self._cache.get(tenant_id)
        if cached is not None:
            info, ts = cached
            if (time.monotonic() - ts) < self._cache_ttl:
                return info if info.status == TenantStatus.ACTIVE else None

        resolved: TenantInfo | None = await self._provider.get_tenant(tenant_id)
        if resolved is not None:
            self._cache[tenant_id] = (resolved, time.monotonic())
            logger.debug(
                "tenant_validated", tenant_id=tenant_id, status=resolved.status
            )
        return (
            resolved
            if resolved is not None and resolved.status == TenantStatus.ACTIVE
            else None
        )

    def invalidate(self, tenant_id: str) -> None:
        """Remove a specific tenant from the cache.

        Args:
            tenant_id: The tenant whose cache entry should be evicted.
        """
        self._cache.pop(tenant_id, None)

    def invalidate_all(self) -> None:
        """Clear the entire validator cache."""
        self._cache.clear()


__all__ = ["TenantValidator"]
