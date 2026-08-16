"""Composite resolver — tries all registered resolvers in priority order."""

from __future__ import annotations

from lexigram.contracts.tenancy.types import TenantResolutionContext
from lexigram.logging import get_logger
from lexigram.tenancy.resolution.registry import ResolverRegistry

logger = get_logger(__name__)


class CompositeResolver:
    """Iterates the :class:`ResolverRegistry` in priority order and returns
    the first non-``None`` result.

    This is the primary resolution entry point used by
    :class:`~lexigram.tenancy.enforcement.middleware.TenantContextMiddleware`.

    Usage::

        resolver = CompositeResolver(registry)
        tenant_id = await resolver.resolve(context)
    """

    def __init__(self, registry: ResolverRegistry) -> None:
        """Initialise with a pre-populated resolver registry.

        Args:
            registry: :class:`~lexigram.tenancy.resolution.registry.ResolverRegistry`
                containing all configured resolvers.
        """
        self._registry = registry

    async def resolve(self, context: TenantResolutionContext) -> str | None:
        """Try each resolver in priority order and return the first result.

        Args:
            context: Immutable snapshot of the current request.

        Returns:
            The resolved ``tenant_id``, or ``None`` if no resolver could
            determine the tenant.
        """
        resolved = await self.resolve_with_source(context)
        return resolved[1] if resolved is not None else None

    async def resolve_with_source(
        self, context: TenantResolutionContext
    ) -> tuple[str, str] | None:
        """Resolve the tenant and report which resolver won.

        Reuses the existing registry priority order.  The resolver *name*
        lets trust-tiered enforcement distinguish a server-verified source
        (``jwt_claim``) from client-influenced ones.

        Args:
            context: Immutable snapshot of the current request.

        Returns:
            ``(resolver_name, tenant_id)`` of the winning resolver, or
            ``None`` when no resolver could determine the tenant.
        """
        for resolver in self._registry.ordered():
            tenant_id = await resolver.resolve(context)
            if tenant_id is not None:
                logger.debug(
                    "tenant_resolved",
                    resolver=resolver.name,
                    tenant_id=tenant_id,
                )
                return (resolver.name, tenant_id)
        return None


__all__ = ["CompositeResolver"]
