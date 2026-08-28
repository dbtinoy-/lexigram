"""Resolver registry for the tenant resolution chain."""

from __future__ import annotations

from collections.abc import Callable

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
    def _resolver_factories(
        cls,
        header_name: str,
        subdomain_pattern: str | None,
        path_pattern: str | None,
        jwt_claim_key: str,
    ) -> dict[str, Callable[[], TenantResolverProtocol]]:
        """Build the name-to-factory dispatch map for the built-in resolvers.

        ``subdomain`` and ``path`` are only selectable when their pattern is
        provided, matching the historical ``from_config`` semantics.

        Args:
            header_name: Header name for the header resolver.
            subdomain_pattern: Base domain for the subdomain resolver.
            path_pattern: Path pattern for the path resolver.
            jwt_claim_key: Claim key for the JWT-claim resolver.

        Returns:
            Mapping of resolver name to a zero-arg factory producing that
            resolver, configured with the given options.
        """
        from lexigram.tenancy.resolution.header import HeaderTenantResolver
        from lexigram.tenancy.resolution.jwt_claim import JWTClaimTenantResolver
        from lexigram.tenancy.resolution.path import PathTenantResolver
        from lexigram.tenancy.resolution.subdomain import SubdomainTenantResolver

        factories: dict[str, Callable[[], TenantResolverProtocol]] = {
            "jwt_claim": lambda: JWTClaimTenantResolver(claim_key=jwt_claim_key),
            "header": lambda: HeaderTenantResolver(header_name=header_name),
        }
        if subdomain_pattern:
            factories["subdomain"] = lambda: SubdomainTenantResolver(
                base_domain=subdomain_pattern
            )
        if path_pattern:
            factories["path"] = lambda: PathTenantResolver(path_pattern=path_pattern)
        return factories

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
        registry = cls()
        factories = cls._resolver_factories(
            header_name=header_name,
            subdomain_pattern=subdomain_pattern,
            path_pattern=path_pattern,
            jwt_claim_key=jwt_claim_key,
        )
        for name in resolver_names:
            factory = factories.get(name)
            if factory is not None:
                registry.register(factory())
        return registry


__all__ = ["ResolverRegistry"]
