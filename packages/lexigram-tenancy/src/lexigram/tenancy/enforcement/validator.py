"""Tenant validator with in-process TTL cache."""

from __future__ import annotations

import time

from lexigram.contracts.tenancy.protocols import (
    TenantMembershipProtocol,
    TenantProviderProtocol,
)
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
        membership: TenantMembershipProtocol | None = None,
        trusted_resolvers: list[str] | None = None,
        strict_membership: bool = True,
    ) -> None:
        """Initialise the validator.

        Args:
            provider: Tenant storage implementing
                :class:`~lexigram.contracts.tenancy.protocols.TenantProviderProtocol`.
            cache_ttl: Seconds to cache a validated
                :class:`~lexigram.contracts.tenancy.types.TenantInfo` record.
                Defaults to 300 seconds.
            membership: Optional membership check.  When ``None`` and
                ``strict_membership`` is ``True``, non-trusted resolvers
                never bind a tenant (default-deny).
            trusted_resolvers: Resolver names exempt from the membership
                check because their source is server-verified.  Defaults
                to ``["jwt_claim"]``.
            strict_membership: When ``True`` (default), deny tenant
                binding when a non-trusted resolver's tenant cannot be
                verified against the caller's identity.  Setting ``False``
                reproduces the pre-fix behavior and is **unsafe** — it is a
                migration-only lever.
        """
        self._provider = provider
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[TenantInfo, float]] = {}
        self._membership = membership
        self._trusted_resolvers = (
            trusted_resolvers if trusted_resolvers is not None else ["jwt_claim"]
        )
        self._strict_membership = strict_membership

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

    async def authorize(
        self,
        *,
        resolver_name: str,
        user_id: str | None,
        tenant_id: str,
    ) -> bool:
        """Decide whether *tenant_id* may be bound to the caller.

        Trusted resolvers are server-verified and bind without further
        checks.  Any other resolver must pass the membership cross-check
        against *user_id*; when strict and verification is impossible
        (no membership protocol bound, or no ``user_id``), the tenant is
        refused — never bound unverified (default-deny).

        Args:
            resolver_name: Name of the resolver that won the chain.
            user_id: Authenticated identity from
                ``scope["state"]["user_id"]`` (``None`` for anonymous).
            tenant_id: The tenant the resolver produced.

        Returns:
            ``True`` if the tenant may be bound, ``False`` otherwise.
        """
        if resolver_name in self._trusted_resolvers:
            return True
        if not self._strict_membership:
            return True
        if self._membership is None or not user_id:
            return False
        return await self._membership.user_belongs_to_tenant(user_id, tenant_id)


__all__ = ["TenantValidator"]
