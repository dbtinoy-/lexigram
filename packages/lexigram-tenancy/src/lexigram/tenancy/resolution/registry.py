"""Resolver registry for the tenant resolution chain."""

from __future__ import annotations

from lexigram.contracts.tenancy.protocols import TenantResolverProtocol


class ResolverRegistry:
    """Ordered registry of :class:`~lexigram.contracts.tenancy.protocols.TenantResolverProtocol` instances.

    Resolvers are stored and returned in ascending ``priority`` order
    (lower number = tried first = higher trust level).

    Usage::

        registry = ResolverRegistry()
        registry.register(HeaderTenantResolver("x-tenant-id"))
        for resolver in registry.ordered():
            ...
    """

    def __init__(self) -> None:
        """Initialise an empty resolver registry."""
        self._resolvers: list[TenantResolverProtocol] = []

    def register(self, resolver: TenantResolverProtocol) -> None:
        """Register a resolver.

        Args:
            resolver: A resolver implementing
                :class:`~lexigram.contracts.tenancy.protocols.TenantResolverProtocol`.
        """
        self._resolvers.append(resolver)

    def ordered(self) -> list[TenantResolverProtocol]:
        """Return resolvers sorted by ascending priority.

        Returns:
            List of resolvers in priority order (lowest number first).
        """
        return sorted(self._resolvers, key=lambda r: r.priority)

    def __len__(self) -> int:
        return len(self._resolvers)

    @classmethod
    def from_config(
        cls,
        resolver_names: list[str],
        header_name: str = "x-tenant-id",
        subdomain_pattern: str | None = None,
        path_pattern: str | None = "/tenants/{tenant_id}/",
        jwt_claim_key: str = "tenant_id",
    ) -> ResolverRegistry:
        """Build a registry from a list of resolver names.

        Only resolvers whose names appear in *resolver_names* are instantiated.
        Unknown names are silently ignored.

        Args:
            resolver_names: Ordered list of resolver names to activate.
            header_name: Header name for :class:`~lexigram.tenancy.resolution.header.HeaderTenantResolver`.
            subdomain_pattern: Base domain for :class:`~lexigram.tenancy.resolution.subdomain.SubdomainTenantResolver`.
            path_pattern: Path pattern for :class:`~lexigram.tenancy.resolution.path.PathTenantResolver`.
            jwt_claim_key: Claim key for :class:`~lexigram.tenancy.resolution.jwt_claim.JWTClaimTenantResolver`.

        Returns:
            A populated :class:`ResolverRegistry`.
        """
        from lexigram.tenancy.resolution.header import HeaderTenantResolver
        from lexigram.tenancy.resolution.jwt_claim import JWTClaimTenantResolver
        from lexigram.tenancy.resolution.path import PathTenantResolver
        from lexigram.tenancy.resolution.subdomain import SubdomainTenantResolver

        registry = cls()
        for name in resolver_names:
            if name == "jwt_claim":
                registry.register(JWTClaimTenantResolver(claim_key=jwt_claim_key))
            elif name == "header":
                registry.register(HeaderTenantResolver(header_name=header_name))
            elif name == "subdomain" and subdomain_pattern:
                registry.register(
                    SubdomainTenantResolver(base_domain=subdomain_pattern)
                )
            elif name == "path" and path_pattern:
                registry.register(PathTenantResolver(path_pattern=path_pattern))
        return registry


__all__ = ["ResolverRegistry"]
