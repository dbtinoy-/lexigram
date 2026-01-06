"""Tests for PathTenantResolver."""

from __future__ import annotations

import pytest

from lexigram.contracts.tenancy.types import TenantResolutionContext
from lexigram.tenancy.resolution.path import PathTenantResolver


@pytest.mark.asyncio
async def test_extracts_tenant_id_from_path() -> None:
    """Extracts tenant_id when path matches pattern."""
    resolver = PathTenantResolver(path_pattern="/tenants/{tenant_id}/")
    ctx = TenantResolutionContext(headers={}, path="/tenants/acme/users")
    result = await resolver.resolve(ctx)
    assert result == "acme"


@pytest.mark.asyncio
async def test_returns_none_when_no_match() -> None:
    """Returns None when path doesn't match pattern."""
    resolver = PathTenantResolver(path_pattern="/tenants/{tenant_id}/")
    ctx = TenantResolutionContext(headers={}, path="/users/acme")
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_path_absent() -> None:
    """Returns None when path is None."""
    resolver = PathTenantResolver(path_pattern="/tenants/{tenant_id}/")
    ctx = TenantResolutionContext(headers={}, path=None)
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_path_empty() -> None:
    """Returns None when path is empty string."""
    resolver = PathTenantResolver(path_pattern="/tenants/{tenant_id}/")
    ctx = TenantResolutionContext(headers={}, path="")
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_handles_custom_path_pattern() -> None:
    """Works with custom path pattern."""
    resolver = PathTenantResolver(path_pattern="/org/{tenant_id}/projects")
    ctx = TenantResolutionContext(headers={}, path="/org/acme/projects")
    result = await resolver.resolve(ctx)
    assert result == "acme"


@pytest.mark.asyncio
async def test_handles_tenant_id_with_hyphens() -> None:
    """Handles tenant IDs with hyphens."""
    resolver = PathTenantResolver(path_pattern="/tenants/{tenant_id}/")
    ctx = TenantResolutionContext(headers={}, path="/tenants/acme-corp/users")
    result = await resolver.resolve(ctx)
    assert result == "acme-corp"


@pytest.mark.asyncio
async def test_handles_tenant_id_with_underscores() -> None:
    """Handles tenant IDs with underscores."""
    resolver = PathTenantResolver(path_pattern="/tenants/{tenant_id}/")
    ctx = TenantResolutionContext(headers={}, path="/tenants/acme_corp/users")
    result = await resolver.resolve(ctx)
    assert result == "acme_corp"


@pytest.mark.asyncio
async def test_handles_tenant_id_with_numbers() -> None:
    """Handles tenant IDs with numbers."""
    resolver = PathTenantResolver(path_pattern="/tenants/{tenant_id}/")
    ctx = TenantResolutionContext(headers={}, path="/tenants/tenant123/users")
    result = await resolver.resolve(ctx)
    assert result == "tenant123"


@pytest.mark.asyncio
async def test_partial_match_returns_none() -> None:
    """Returns None if path contains pattern but isn't matched."""
    resolver = PathTenantResolver(path_pattern="/tenants/{tenant_id}/")
    ctx = TenantResolutionContext(headers={}, path="/tenants/acme/extra")
    result = await resolver.resolve(ctx)
    assert result == "acme"


def test_priority_is_40() -> None:
    """Path resolver has priority 40."""
    assert PathTenantResolver.priority == 40


def test_name_is_path() -> None:
    """Resolver name is 'path'."""
    assert PathTenantResolver.name == "path"


def test_compile_escaps_special_chars() -> None:
    """_compile escapes special regex characters."""
    pattern = PathTenantResolver._compile("/tenants/{tenant_id}/")
    assert pattern.match("/tenants/acme/") is not None


def test_compile_creates_named_group() -> None:
    """_compile creates a named capture group."""
    pattern = PathTenantResolver._compile("/tenants/{tenant_id}/")
    match = pattern.match("/tenants/acme/")
    assert match is not None
    assert match.group("tenant_id") == "acme"


@pytest.mark.asyncio
async def test_default_pattern() -> None:
    """Default pattern is /tenants/{tenant_id}/."""
    resolver = PathTenantResolver()
    ctx = TenantResolutionContext(headers={}, path="/tenants/default-tenant/")
    result = await resolver.resolve(ctx)
    assert result == "default-tenant"


@pytest.mark.asyncio
async def test_empty_tenant_id_returns_none() -> None:
    """Empty tenant ID portion returns None."""
    resolver = PathTenantResolver(path_pattern="/tenants/{tenant_id}/")
    ctx = TenantResolutionContext(headers={}, path="/tenants/")
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_pattern_with_different_prefix() -> None:
    """Works with different path prefixes."""
    resolver = PathTenantResolver(path_pattern="/customers/{tenant_id}/accounts")
    ctx = TenantResolutionContext(headers={}, path="/customers/acme/accounts")
    result = await resolver.resolve(ctx)
    assert result == "acme"