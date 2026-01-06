"""Tests for JWTClaimTenantResolver."""

from __future__ import annotations

import pytest

from lexigram.contracts.tenancy.types import TenantResolutionContext
from lexigram.tenancy.resolution.jwt_claim import JWTClaimTenantResolver


@pytest.mark.asyncio
async def test_resolves_from_claim() -> None:
    """Returns the claim value when present in context.claims."""
    resolver = JWTClaimTenantResolver(claim_key="tenant_id")
    ctx = TenantResolutionContext(headers={}, claims={"tenant_id": "tenant-xyz"})
    result = await resolver.resolve(ctx)
    assert result == "tenant-xyz"


@pytest.mark.asyncio
async def test_returns_none_when_claim_absent() -> None:
    """Returns None when the claim key is not in claims."""
    resolver = JWTClaimTenantResolver()
    ctx = TenantResolutionContext(headers={}, claims={})
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_converts_non_string_claim_to_str() -> None:
    """Integer claim values are coerced to str."""
    resolver = JWTClaimTenantResolver()
    ctx = TenantResolutionContext(headers={}, claims={"tenant_id": 42})
    result = await resolver.resolve(ctx)
    assert result == "42"


@pytest.mark.asyncio
async def test_custom_claim_key() -> None:
    """Custom claim key is respected."""
    resolver = JWTClaimTenantResolver(claim_key="org_id")
    ctx = TenantResolutionContext(headers={}, claims={"org_id": "org-456"})
    result = await resolver.resolve(ctx)
    assert result == "org-456"


def test_priority_is_10() -> None:
    """JWT claim resolver has priority 10 (highest default trust)."""
    assert JWTClaimTenantResolver.priority == 10


@pytest.mark.asyncio
async def test_returns_none_for_falsy_claim_value() -> None:
    """Returns None for falsy claim values like 0 or False."""
    resolver = JWTClaimTenantResolver(claim_key="tenant_id")
    ctx = TenantResolutionContext(headers={}, claims={"tenant_id": 0})
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_for_empty_string_claim() -> None:
    """Returns None for empty string claim value."""
    resolver = JWTClaimTenantResolver(claim_key="tenant_id")
    ctx = TenantResolutionContext(headers={}, claims={"tenant_id": ""})
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_for_none_claim_value() -> None:
    """Returns None when claim value is explicitly None."""
    resolver = JWTClaimTenantResolver(claim_key="tenant_id")
    ctx = TenantResolutionContext(headers={}, claims={"tenant_id": None})
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_converts_float_claim_to_str() -> None:
    """Float claim values are converted to str."""
    resolver = JWTClaimTenantResolver(claim_key="tenant_id")
    ctx = TenantResolutionContext(headers={}, claims={"tenant_id": 3.14})
    result = await resolver.resolve(ctx)
    assert result == "3.14"


@pytest.mark.asyncio
async def test_default_claim_key_is_tenant_id() -> None:
    """Default claim key is 'tenant_id'."""
    resolver = JWTClaimTenantResolver()
    ctx = TenantResolutionContext(headers={}, claims={"tenant_id": "default-tenant"})
    result = await resolver.resolve(ctx)
    assert result == "default-tenant"


@pytest.mark.asyncio
async def test_claims_with_multiple_values() -> None:
    """Works when claims contains multiple values."""
    resolver = JWTClaimTenantResolver(claim_key="tenant_id")
    ctx = TenantResolutionContext(
        headers={},
        claims={"sub": "user-123", "tenant_id": "tenant-xyz", "exp": 1234567890},
    )
    result = await resolver.resolve(ctx)
    assert result == "tenant-xyz"


def test_name_is_jwt_claim() -> None:
    """Resolver name is 'jwt_claim'."""
    assert JWTClaimTenantResolver.name == "jwt_claim"


@pytest.mark.asyncio
async def test_claims_with_nested_objects() -> None:
    """Works when claims contain nested objects."""
    resolver = JWTClaimTenantResolver(claim_key="tenant_id")
    ctx = TenantResolutionContext(
        headers={},
        claims={"tenant_id": {"id": "tenant-xyz"}},
    )
    result = await resolver.resolve(ctx)
    assert result == "{'id': 'tenant-xyz'}"


@pytest.mark.asyncio
async def test_returns_none_when_claim_is_list() -> None:
    """Returns None when claim is a list."""
    resolver = JWTClaimTenantResolver(claim_key="tenant_id")
    ctx = TenantResolutionContext(headers={}, claims={"tenant_id": ["a", "b"]})
    result = await resolver.resolve(ctx)
    assert result == "['a', 'b']"
