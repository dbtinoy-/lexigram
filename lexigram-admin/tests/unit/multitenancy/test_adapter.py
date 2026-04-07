"""Tests for TenantProviderRegistry and resolve_tenant_id."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from lexigram.admin.multitenancy.adapter import (
    TenantProviderRegistry,
    _to_tenant_config,
    resolve_tenant_id,
)
from lexigram.admin.multitenancy.models import TenantConfig, TenantNotFoundError
from lexigram.contracts.tenancy.commands import CreateTenantCommand
from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus

# ---------------------------------------------------------------------------
# Fake provider for delegation tests
# ---------------------------------------------------------------------------


class _FakeTenantProvider:
    """Minimal ``TenantProviderProtocol`` implementation backed by a dict."""

    def __init__(self) -> None:
        self._store: dict[str, TenantInfo] = {}
        self.last_command: CreateTenantCommand | None = None

    async def get_tenant(self, tenant_id: str) -> TenantInfo | None:
        return self._store.get(tenant_id)

    async def list_tenants(self, *, active_only: bool = True) -> list[TenantInfo]:
        tenants = list(self._store.values())
        if active_only:
            return [t for t in tenants if t.status == TenantStatus.ACTIVE]
        return tenants

    async def create_tenant(self, command: CreateTenantCommand) -> TenantInfo:
        from lexigram.contracts.core.result import Ok

        self.last_command = command
        info = TenantInfo(
            tenant_id=command.slug,
            slug=command.slug,
            name=command.name,
            status=TenantStatus.ACTIVE,
            config=command.config,
            metadata=command.metadata,
            created_at=datetime.now(UTC),
        )
        self._store[command.slug] = info
        return Ok(info)

    async def deactivate_tenant(self, tenant_id: str) -> TenantInfo:
        from lexigram.contracts.core.result import Ok

        info = self._store.get(tenant_id)
        if info:
            self._store[tenant_id] = TenantInfo(
                tenant_id=info.tenant_id,
                slug=info.slug,
                name=info.name,
                status=TenantStatus.INACTIVE,
                config=info.config,
                metadata=info.metadata,
                created_at=info.created_at,
            )
        return Ok(None)


# ---------------------------------------------------------------------------
# _to_tenant_config
# ---------------------------------------------------------------------------


class TestToTenantConfig:
    def test_converts_tenant_info(self) -> None:
        info = TenantInfo(
            tenant_id="acme",
            slug="acme",
            name="Acme Corp",
            status=TenantStatus.ACTIVE,
            config={"domain": "acme.example.com"},
            metadata={"plan": "enterprise"},
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        cfg = _to_tenant_config(info)
        assert cfg.tenant_id == "acme"
        assert cfg.name == "Acme Corp"
        assert cfg.domain == "acme.example.com"
        assert cfg.active is True
        assert cfg.metadata == {"plan": "enterprise"}

    def test_converts_inactive_tenant(self) -> None:
        info = TenantInfo(
            tenant_id="beta",
            slug="beta",
            name="Beta Inc",
            status=TenantStatus.INACTIVE,
        )
        cfg = _to_tenant_config(info)
        assert cfg.active is False


# ---------------------------------------------------------------------------
# TenantProviderRegistry — without provider (in-memory only)
# ---------------------------------------------------------------------------


class TestTenantProviderRegistryInMemory:
    @pytest.fixture
    def registry(self) -> TenantProviderRegistry:
        return TenantProviderRegistry()

    @pytest.mark.asyncio
    async def test_add_and_get(self, registry: TenantProviderRegistry) -> None:
        cfg = TenantConfig(tenant_id="acme", name="Acme Corp")
        await registry.add(cfg)
        assert registry._tenants["acme"] is cfg

    @pytest.mark.asyncio
    async def test_get_missing(self, registry: TenantProviderRegistry) -> None:
        assert await registry.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_or_raise_ok(self, registry: TenantProviderRegistry) -> None:
        cfg = TenantConfig(tenant_id="a", name="A")
        await registry.add(cfg)
        assert await registry.get_or_raise("a") is cfg

    @pytest.mark.asyncio
    async def test_get_or_raise_missing(self, registry: TenantProviderRegistry) -> None:
        with pytest.raises(TenantNotFoundError):
            await registry.get_or_raise("missing")

    @pytest.mark.asyncio
    async def test_remove(self, registry: TenantProviderRegistry) -> None:
        cfg = TenantConfig(tenant_id="a", name="A")
        await registry.add(cfg)
        removed = await registry.remove("a")
        assert removed is cfg
        assert "a" not in registry._tenants

    @pytest.mark.asyncio
    async def test_remove_missing_raises(self, registry: TenantProviderRegistry) -> None:
        with pytest.raises(TenantNotFoundError):
            await registry.remove("missing")

    @pytest.mark.asyncio
    async def test_all(self, registry: TenantProviderRegistry) -> None:
        await registry.add(TenantConfig(tenant_id="a", name="A"))
        await registry.add(TenantConfig(tenant_id="b", name="B"))
        tenants = await registry.all()
        assert len(tenants) == 2

    @pytest.mark.asyncio
    async def test_all_active_only(self, registry: TenantProviderRegistry) -> None:
        await registry.add(TenantConfig(tenant_id="a", name="A", active=True))
        await registry.add(TenantConfig(tenant_id="b", name="B", active=False))
        result = await registry.all(active_only=True)
        assert len(result) == 1
        assert result[0].tenant_id == "a"

    @pytest.mark.asyncio
    async def test_exists(self, registry: TenantProviderRegistry) -> None:
        await registry.add(TenantConfig(tenant_id="x", name="X"))
        assert registry.exists("x") is True
        assert registry.exists("y") is False

    @pytest.mark.asyncio
    async def test_get_by_domain(self, registry: TenantProviderRegistry) -> None:
        cfg = TenantConfig(tenant_id="a", name="A", domain="a.example.com")
        await registry.add(cfg)
        assert registry.get_by_domain("a.example.com") is cfg
        assert registry.get_by_domain("other.com") is None

    @pytest.mark.asyncio
    async def test_domain_index_cleaned_on_remove(self, registry: TenantProviderRegistry) -> None:
        cfg = TenantConfig(tenant_id="a", name="A", domain="a.example.com")
        await registry.add(cfg)
        await registry.remove("a")
        assert registry.get_by_domain("a.example.com") is None


# ---------------------------------------------------------------------------
# TenantProviderRegistry — with provider (delegation enabled)
# ---------------------------------------------------------------------------


class TestTenantProviderRegistryWithProvider:
    @pytest.fixture
    def provider(self) -> _FakeTenantProvider:
        return _FakeTenantProvider()

    @pytest.fixture
    def registry(self, provider: _FakeTenantProvider) -> TenantProviderRegistry:
        return TenantProviderRegistry(provider=provider)

    @pytest.mark.asyncio
    async def test_add_delegates_to_provider(
        self, registry: TenantProviderRegistry, provider: _FakeTenantProvider
    ) -> None:
        cfg = TenantConfig(tenant_id="acme", name="Acme Corp")
        await registry.add(cfg)
        assert provider.last_command is not None
        assert provider.last_command.slug == "acme"
        assert provider.last_command.name == "Acme Corp"

    @pytest.mark.asyncio
    async def test_get_falls_through_to_provider(
        self, registry: TenantProviderRegistry, provider: _FakeTenantProvider
    ) -> None:
        cfg = TenantConfig(tenant_id="acme", name="Acme Corp")
        await registry.add(cfg)
        result = await registry.get("acme")
        assert result is not None
        assert result.tenant_id == "acme"

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_in_provider(
        self, registry: TenantProviderRegistry, provider: _FakeTenantProvider
    ) -> None:
        result = await registry.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_remove_updates_provider(
        self, registry: TenantProviderRegistry, provider: _FakeTenantProvider
    ) -> None:
        cfg = TenantConfig(tenant_id="acme", name="Acme Corp")
        await registry.add(cfg)
        await registry.remove("acme")
        assert "acme" not in registry._tenants

    @pytest.mark.asyncio
    async def test_all_delegates_to_provider(
        self, registry: TenantProviderRegistry, provider: _FakeTenantProvider
    ) -> None:
        await registry.add(TenantConfig(tenant_id="a", name="A"))
        await registry.add(TenantConfig(tenant_id="b", name="B"))
        tenants = await registry.all()
        assert len(tenants) >= 2

    @pytest.mark.asyncio
    async def test_exists_checks_cache_only(
        self, registry: TenantProviderRegistry, provider: _FakeTenantProvider
    ) -> None:
        assert registry.exists("a") is False
        await registry.add(TenantConfig(tenant_id="a", name="A"))
        assert registry.exists("a") is True


# ---------------------------------------------------------------------------
# resolve_tenant_id
# ---------------------------------------------------------------------------


class TestResolveTenantId:
    @pytest.mark.asyncio
    async def test_state_tenant_id(self) -> None:
        request = _req(state_tenant="from_state")
        assert await resolve_tenant_id(request) == "from_state"

    @pytest.mark.asyncio
    async def test_header_tenant_id(self) -> None:
        request = _req(headers={"x-tenant-id": "from_header"})
        assert await resolve_tenant_id(request) == "from_header"

    @pytest.mark.asyncio
    async def test_custom_header_name(self) -> None:
        request = _req(headers={"x-org": "org-42"})
        assert await resolve_tenant_id(request, header="x-org") == "org-42"

    @pytest.mark.asyncio
    async def test_cookie_tenant_id(self) -> None:
        request = _req(cookies={"admin_tenant": "from_cookie"})
        assert await resolve_tenant_id(request) == "from_cookie"

    @pytest.mark.asyncio
    async def test_custom_cookie_name(self) -> None:
        request = _req(cookies={"org": "org-99"})
        assert await resolve_tenant_id(request, cookie="org") == "org-99"

    @pytest.mark.asyncio
    async def test_header_before_cookie(self) -> None:
        request = _req(
            headers={"x-tenant-id": "from_header"},
            cookies={"admin_tenant": "from_cookie"},
        )
        assert await resolve_tenant_id(request) == "from_header"

    @pytest.mark.asyncio
    async def test_default_when_nothing(self) -> None:
        request = _req()
        assert await resolve_tenant_id(request) == ""

    @pytest.mark.asyncio
    async def test_custom_default(self) -> None:
        request = _req()
        assert await resolve_tenant_id(request, default="fallback") == "fallback"

    @pytest.mark.asyncio
    async def test_subdomain_resolves_via_registry(self) -> None:
        """Subdomain lookup should resolve via TenantProviderRegistry on app state."""
        from lexigram.admin.multitenancy.adapter import TenantProviderRegistry

        reg = TenantProviderRegistry()
        await reg.add(TenantConfig(tenant_id="acme", name="Acme", domain="acme.example.com"))
        request = _req(hostname="acme.example.com", registry=reg)
        assert await resolve_tenant_id(request) == "acme"

    @pytest.mark.asyncio
    async def test_subdomain_skipped_when_no_registry(self) -> None:
        """Subdomain resolution should be skipped when no registry on app state."""
        request = _req(hostname="acme.example.com")
        assert await resolve_tenant_id(request) == ""

    @pytest.mark.asyncio
    async def test_subdomain_skipped_for_short_hostname(self) -> None:
        """Subdomain logic should skip hostnames with fewer than 3 parts."""
        request = _req(hostname="example.com")
        assert await resolve_tenant_id(request) == ""

    @pytest.mark.asyncio
    async def test_no_state_attribute(self) -> None:
        """Resolver should handle request without a state attribute."""
        request = MagicMock(spec=[])
        request.headers = {"x-tenant-id": "from_header"}
        assert await resolve_tenant_id(request) == "from_header"

    @pytest.mark.asyncio
    async def test_no_headers_attr(self) -> None:
        """Resolver should handle request without headers."""
        request = MagicMock(spec=[])
        request.cookies = {"admin_tenant": "from_cookie"}
        assert await resolve_tenant_id(request) == "from_cookie"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _req(
    state_tenant: str = "",
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    hostname: str | None = None,
    registry: object | None = None,
) -> MagicMock:
    """Build a minimal Starlette-like request mock."""
    req = MagicMock(spec=[])
    req.state = MagicMock()
    req.state.tenant_id = state_tenant or None
    req.headers = headers or {}
    req.cookies = cookies or {}
    url = MagicMock()
    url.hostname = hostname
    req.url = url

    if registry is not None:
        app_state = MagicMock()
        app_state.tenant_registry = registry
        req.app = MagicMock()
        req.app.state = app_state

    return req
