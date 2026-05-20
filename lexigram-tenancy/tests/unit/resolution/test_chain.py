"""Tests for CompositeResolver."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.contracts.tenancy.types import TenantResolutionContext
from lexigram.tenancy.resolution.chain import CompositeResolver
from lexigram.tenancy.resolution.registry import ResolverRegistry


class _ImmediateResolver:
    name = "immediate"
    priority = 5

    async def resolve(self, context: TenantResolutionContext) -> str | None:
        return "immediate-result"


class _FailingResolver:
    name = "fail"
    priority = 15

    async def resolve(self, context: TenantResolutionContext) -> str | None:
        return None


@pytest.mark.asyncio
async def test_returns_first_non_none_result() -> None:
    """Returns the result of the first resolver that succeeds."""
    registry = ResolverRegistry.from_config(
        resolver_names=["jwt_claim", "header"],
        jwt_claim_key="tenant_id",
    )
    resolver = CompositeResolver(registry)
    ctx = TenantResolutionContext(
        headers={"x-tenant-id": "from-header"},
        claims={"tenant_id": "from-jwt"},
    )
    result = await resolver.resolve(ctx)
    # jwt_claim (priority 10) should win over header (priority 20)
    assert result == "from-jwt"


@pytest.mark.asyncio
async def test_falls_through_to_next_resolver() -> None:
    """Falls through to the next resolver when the first returns None."""
    registry = ResolverRegistry.from_config(
        resolver_names=["jwt_claim", "header"],
    )
    resolver = CompositeResolver(registry)
    ctx = TenantResolutionContext(
        headers={"x-tenant-id": "from-header"},
        claims={},  # no jwt claim
    )
    result = await resolver.resolve(ctx)
    assert result == "from-header"


@pytest.mark.asyncio
async def test_returns_none_when_all_resolvers_fail() -> None:
    """Returns None when no resolver can determine the tenant."""
    registry = ResolverRegistry.from_config(resolver_names=["header"])
    resolver = CompositeResolver(registry)
    ctx = TenantResolutionContext(headers={})
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_empty_registry_returns_none() -> None:
    """Returns None immediately when the registry is empty."""
    registry = ResolverRegistry()
    resolver = CompositeResolver(registry)
    ctx = TenantResolutionContext(headers={})
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_resolver_stops_on_first_non_none() -> None:
    """Stops after the first successful resolver."""
    call_counts: dict[str, int] = {}

    class _CountingResolver:
        name = "counting"
        priority = 10

        def __init__(self, name: str, should_succeed: bool) -> None:
            self._name = name
            self._should_succeed = should_succeed

        async def resolve(self, context: TenantResolutionContext) -> str | None:
            call_counts[self._name] = call_counts.get(self._name, 0) + 1
            if self._should_succeed:
                return "result"
            return None

    registry = ResolverRegistry()
    registry.register(_CountingResolver("first", True))
    registry.register(_CountingResolver("second", False))  # Would be called if first fails

    composite = CompositeResolver(registry)
    ctx = TenantResolutionContext(headers={})
    result = await composite.resolve(ctx)

    assert result == "result"
    assert call_counts["first"] == 1
    assert call_counts.get("second", 0) == 0


@pytest.mark.asyncio
async def test_ordered_by_priority() -> None:
    """Resolvers are called in priority order - lower priority first."""
    call_order: list[str] = []

    class _FirstResolver:
        name = "first"
        priority = 10

        async def resolve(self, context: TenantResolutionContext) -> str | None:
            call_order.append("first")
            return "result"

    class _SecondResolver:
        name = "second"
        priority = 20

        async def resolve(self, context: TenantResolutionContext) -> str | None:
            call_order.append("second")
            return None

    registry = ResolverRegistry()
    registry.register(_SecondResolver())  # Higher priority, should be called second
    registry.register(_FirstResolver())  # Lower priority, should be called first

    composite = CompositeResolver(registry)
    ctx = TenantResolutionContext(headers={})
    result = await composite.resolve(ctx)

    assert result == "result"
    assert call_order[0] == "first"


@pytest.mark.asyncio
async def test_with_custom_resolver_registry() -> None:
    """Works with custom resolver instances."""
    registry = ResolverRegistry()
    registry.register(_ImmediateResolver())

    composite = CompositeResolver(registry)
    ctx = TenantResolutionContext(headers={})
    result = await composite.resolve(ctx)

    assert result == "immediate-result"


@pytest.mark.asyncio
async def test_multiple_resolvers_all_return_none() -> None:
    """Returns None when all resolvers return None."""
    registry = ResolverRegistry()
    for i in range(3):
        registry.register(_FailingResolver())

    composite = CompositeResolver(registry)
    ctx = TenantResolutionContext(headers={})
    result = await composite.resolve(ctx)

    assert result is None


@pytest.mark.asyncio
async def test_resolve_with_source_returns_name_and_tenant() -> None:
    registry = ResolverRegistry.from_config(resolver_names=["jwt_claim", "header"])
    resolver = CompositeResolver(registry)
    ctx = TenantResolutionContext(headers={"x-tenant-id": "from-header"}, claims={"tenant_id": "from-jwt"})
    assert await resolver.resolve_with_source(ctx) == ("jwt_claim", "from-jwt")


@pytest.mark.asyncio
async def test_resolve_with_source_falls_through() -> None:
    registry = ResolverRegistry.from_config(resolver_names=["jwt_claim", "header"])
    resolver = CompositeResolver(registry)
    ctx = TenantResolutionContext(headers={"x-tenant-id": "from-header"}, claims={})
    assert await resolver.resolve_with_source(ctx) == ("header", "from-header")


@pytest.mark.asyncio
async def test_resolve_with_source_none_when_fails() -> None:
    registry = ResolverRegistry.from_config(resolver_names=["header"])
    resolver = CompositeResolver(registry)
    assert await resolver.resolve_with_source(TenantResolutionContext(headers={})) is None


@pytest.mark.asyncio
async def test_resolve_delegates_to_resolve_with_source() -> None:
    registry = ResolverRegistry.from_config(resolver_names=["header"])
    resolver = CompositeResolver(registry)
    ctx = TenantResolutionContext(headers={"x-tenant-id": "from-header"})
    assert await resolver.resolve(ctx) == "from-header"
