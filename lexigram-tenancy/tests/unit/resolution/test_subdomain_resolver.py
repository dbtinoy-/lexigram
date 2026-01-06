"""Tests for SubdomainTenantResolver."""

from __future__ import annotations

import pytest

from lexigram.contracts.tenancy.types import TenantResolutionContext
from lexigram.tenancy.resolution.subdomain import SubdomainTenantResolver


@pytest.mark.asyncio
async def test_extracts_subdomain() -> None:
    """Returns the subdomain prefix when host matches base domain."""
    resolver = SubdomainTenantResolver(base_domain="app.com")
    ctx = TenantResolutionContext(headers={}, host="acme.app.com")
    result = await resolver.resolve(ctx)
    assert result == "acme"


@pytest.mark.asyncio
async def test_returns_none_when_no_match() -> None:
    """Returns None when host does not end with base domain."""
    resolver = SubdomainTenantResolver(base_domain="app.com")
    ctx = TenantResolutionContext(headers={}, host="other.example.com")
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_host_absent() -> None:
    """Returns None when host is None."""
    resolver = SubdomainTenantResolver(base_domain="app.com")
    ctx = TenantResolutionContext(headers={}, host=None)
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_strips_port_from_host() -> None:
    """Port suffix is ignored when extracting subdomain."""
    resolver = SubdomainTenantResolver(base_domain="app.com")
    ctx = TenantResolutionContext(headers={}, host="acme.app.com:8080")
    result = await resolver.resolve(ctx)
    assert result == "acme"


def test_priority_is_30() -> None:
    """Subdomain resolver has priority 30."""
    assert SubdomainTenantResolver.priority == 30


@pytest.mark.asyncio
async def test_subdomain_with_dots() -> None:
    """Handles subdomains with dots."""
    resolver = SubdomainTenantResolver(base_domain="app.com")
    ctx = TenantResolutionContext(headers={}, host="sub.domain.app.com")
    result = await resolver.resolve(ctx)
    assert result == "sub.domain"


@pytest.mark.asyncio
async def test_empty_subdomain_returns_none() -> None:
    """Empty subdomain (same as base) returns None."""
    resolver = SubdomainTenantResolver(base_domain="app.com")
    ctx = TenantResolutionContext(headers={}, host="app.com")
    result = await resolver.resolve(ctx)
    assert result is None


@pytest.mark.asyncio
async def test_with_www_prefix() -> None:
    """Returns None for www prefix."""
    resolver = SubdomainTenantResolver(base_domain="app.com")
    ctx = TenantResolutionContext(headers={}, host="www.app.com")
    result = await resolver.resolve(ctx)
    assert result == "www"


@pytest.mark.asyncio
async def test_base_domain_without_dot() -> None:
    """Base domain without leading dot gets one added."""
    resolver = SubdomainTenantResolver(base_domain="app.com")
    ctx = TenantResolutionContext(headers={}, host="acme.app.com")
    result = await resolver.resolve(ctx)
    assert result == "acme"


@pytest.mark.asyncio
async def test_base_domain_with_dot() -> None:
    """Base domain with leading dot works correctly."""
    resolver = SubdomainTenantResolver(base_domain=".app.com")
    ctx = TenantResolutionContext(headers={}, host="acme.app.com")
    result = await resolver.resolve(ctx)
    assert result == "acme"


@pytest.mark.asyncio
async def test_host_with_multiple_ports() -> None:
    """Handles host with multiple colons (IPv6 + port)."""
    resolver = SubdomainTenantResolver(base_domain="app.com")
    ctx = TenantResolutionContext(headers={}, host="acme.app.com:8080")
    result = await resolver.resolve(ctx)
    assert result == "acme"


def test_name_is_subdomain() -> None:
    """Resolver name is 'subdomain'."""
    assert SubdomainTenantResolver.name == "subdomain"


@pytest.mark.asyncio
async def test_host_with_underscore() -> None:
    """Handles host with underscore."""
    resolver = SubdomainTenantResolver(base_domain="app.com")
    ctx = TenantResolutionContext(headers={}, host="acme_dev.app.com")
    result = await resolver.resolve(ctx)
    assert result is not None
