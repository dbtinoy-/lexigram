"""Tests for HeaderTenantResolver."""

from __future__ import annotations

import pytest

from lexigram.contracts.tenancy.types import TenantResolutionContext
from lexigram.tenancy.resolution.header import HeaderTenantResolver


@pytest.mark.asyncio
async def test_extracts_tenant_from_header() -> None:
    """Returns header value when present."""
    resolver = HeaderTenantResolver(header_name="x-tenant-id")
    ctx = TenantResolutionContext(headers={"x-tenant-id": "tenant-abc"})
    result = await resolver.resolve(ctx)
    assert result == "tenant-abc"


@pytest.mark.asyncio
async def test_returns_none_when_header_absent() -> None:
    """Returns None when header is missing."""
    resolver = HeaderTenantResolver(header_name="x-tenant-id")
    ctx = TenantResolutionContext(headers={})
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_strips_whitespace_from_value() -> None:
    """Strips whitespace from header value."""
    resolver = HeaderTenantResolver(header_name="x-tenant-id")
    ctx = TenantResolutionContext(headers={"x-tenant-id": "  tenant-abc  "})
    result = await resolver.resolve(ctx)
    assert result == "tenant-abc"


@pytest.mark.asyncio
async def test_returns_none_when_value_only_whitespace() -> None:
    """Returns None when value is only whitespace."""
    resolver = HeaderTenantResolver(header_name="x-tenant-id")
    ctx = TenantResolutionContext(headers={"x-tenant-id": "   "})
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_value_empty() -> None:
    """Returns None when value is empty string."""
    resolver = HeaderTenantResolver(header_name="x-tenant-id")
    ctx = TenantResolutionContext(headers={"x-tenant-id": ""})
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_header_name_is_lowercased() -> None:
    """Header name is lowercased on init."""
    resolver = HeaderTenantResolver(header_name="X-Tenant-ID")
    ctx = TenantResolutionContext(headers={"x-tenant-id": "tenant-xyz"})
    result = await resolver.resolve(ctx)
    assert result == "tenant-xyz"


@pytest.mark.asyncio
async def test_custom_header_name() -> None:
    """Works with custom header name."""
    resolver = HeaderTenantResolver(header_name="x-org-id")
    ctx = TenantResolutionContext(headers={"x-org-id": "org-123"})
    result = await resolver.resolve(ctx)
    assert result == "org-123"


@pytest.mark.asyncio
async def test_default_header_name() -> None:
    """Default header name is x-tenant-id."""
    resolver = HeaderTenantResolver()
    ctx = TenantResolutionContext(headers={"x-tenant-id": "default-tenant"})
    result = await resolver.resolve(ctx)
    assert result == "default-tenant"


def test_priority_is_20() -> None:
    """Header resolver has priority 20."""
    assert HeaderTenantResolver.priority == 20


def test_name_is_header() -> None:
    """Resolver name is 'header'."""
    assert HeaderTenantResolver.name == "header"


@pytest.mark.asyncio
async def test_header_value_not_modified() -> None:
    """Original header value is not modified."""
    resolver = HeaderTenantResolver(header_name="x-tenant-id")
    ctx = TenantResolutionContext(headers={"x-tenant-id": "tenant-xyz"})
    result = await resolver.resolve(ctx)
    assert result == "tenant-xyz"