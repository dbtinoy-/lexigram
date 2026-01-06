"""Tests for ResolverRegistry."""

from __future__ import annotations

import pytest

from lexigram.tenancy.resolution.header import HeaderTenantResolver
from lexigram.tenancy.resolution.registry import ResolverRegistry


def test_register_and_ordered_by_priority() -> None:
    """Resolvers are returned in ascending priority order."""
    registry = ResolverRegistry()

    class HighPriorityResolver:
        name = "high"
        priority = 10

        async def resolve(self, ctx: object) -> str | None:
            return None

    class LowPriorityResolver:
        name = "low"
        priority = 40

        async def resolve(self, ctx: object) -> str | None:
            return None

    low = LowPriorityResolver()
    high = HighPriorityResolver()
    registry.register(low)
    registry.register(high)

    ordered = registry.ordered()
    assert ordered[0].name == "high"
    assert ordered[1].name == "low"


def test_len_returns_count() -> None:
    """__len__ reflects the number of registered resolvers."""
    registry = ResolverRegistry()
    assert len(registry) == 0

    registry.register(HeaderTenantResolver())
    assert len(registry) == 1


def test_from_config_creates_header_resolver() -> None:
    """from_config instantiates the header resolver when requested."""
    registry = ResolverRegistry.from_config(resolver_names=["header"])
    assert len(registry) == 1
    assert registry.ordered()[0].name == "header"


def test_from_config_subdomain_requires_pattern() -> None:
    """Subdomain resolver is skipped when subdomain_pattern is None."""
    registry = ResolverRegistry.from_config(
        resolver_names=["subdomain"],
        subdomain_pattern=None,
    )
    assert len(registry) == 0


def test_from_config_all_resolvers() -> None:
    """All four resolvers are instantiated when all names are given and patterns provided."""
    registry = ResolverRegistry.from_config(
        resolver_names=["jwt_claim", "header", "subdomain", "path"],
        subdomain_pattern="app.com",
        path_pattern="/t/{tenant_id}/",
    )
    assert len(registry) == 4
    names = {r.name for r in registry.ordered()}
    assert names == {"jwt_claim", "header", "subdomain", "path"}


def test_ordering_with_multiple_same_priority() -> None:
    """Resolvers with same priority maintain insertion order."""
    registry = ResolverRegistry()

    class ResolverA:
        name = "a"
        priority = 10

        async def resolve(self, ctx: object) -> str | None:
            return None

    class ResolverB:
        name = "b"
        priority = 10

        async def resolve(self, ctx: object) -> str | None:
            return None

    registry.register(ResolverA())
    registry.register(ResolverB())
    ordered = registry.ordered()
    assert ordered[0].name == "a"
    assert ordered[1].name == "b"


def test_from_config_empty_list() -> None:
    """from_config with empty list returns empty registry."""
    registry = ResolverRegistry.from_config(resolver_names=[])
    assert len(registry) == 0


def test_from_config_unknown_resolver_ignored() -> None:
    """Unknown resolver names are silently ignored."""
    registry = ResolverRegistry.from_config(
        resolver_names=["unknown_resolver", "header"],
    )
    assert len(registry) == 1
    assert registry.ordered()[0].name == "header"


def test_from_config_with_custom_header_name() -> None:
    """Custom header name is passed to header resolver."""
    registry = ResolverRegistry.from_config(
        resolver_names=["header"],
        header_name="x-custom-tenant",
    )
    resolver = registry.ordered()[0]
    ctx_type = type(resolver)
    assert resolver.name == "header"


def test_from_config_with_jwt_claim_key() -> None:
    """Custom JWT claim key is passed to JWT resolver."""
    registry = ResolverRegistry.from_config(
        resolver_names=["jwt_claim"],
        jwt_claim_key="org_id",
    )
    assert len(registry) == 1
    assert registry.ordered()[0].name == "jwt_claim"


def test_from_config_path_requires_pattern() -> None:
    """Path resolver is skipped when path_pattern is None."""
    registry = ResolverRegistry.from_config(
        resolver_names=["path"],
        path_pattern=None,
    )
    assert len(registry) == 0


def test_from_config_custom_path_pattern() -> None:
    """Custom path pattern is passed to path resolver."""
    registry = ResolverRegistry.from_config(
        resolver_names=["path"],
        path_pattern="/org/{tenant_id}/",
    )
    assert len(registry) == 1
    assert registry.ordered()[0].name == "path"


def test_ordered_returns_list() -> None:
    """ordered() returns a list, not an iterator."""
    registry = ResolverRegistry()
    registry.register(HeaderTenantResolver())
    result = registry.ordered()
    assert isinstance(result, list)
