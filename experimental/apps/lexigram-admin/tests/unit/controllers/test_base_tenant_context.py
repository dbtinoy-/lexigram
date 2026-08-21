"""Tests for AdminController._apply_tenant_context."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.controllers.base import AdminController


def _make_controller() -> AdminController:
    return AdminController(renderer=MagicMock())


def _make_request(
    *,
    container: MagicMock,
    user: SimpleNamespace | None,
    tenant_id: str | None = None,
) -> MagicMock:
    request = MagicMock()
    request.state = SimpleNamespace(container=container, user=user, tenant_id=tenant_id)
    request.session = {"admin_user_id": "u1"}
    request.headers = {}
    request.cookies = {}
    return request


class TestApplyTenantContext:
    @pytest.mark.asyncio
    async def test_noop_when_tenancy_disabled(self) -> None:
        from lexigram.admin.config import AdminConfig

        config = AdminConfig()
        config.tenancy.enabled = False
        container = MagicMock()
        container.resolve = AsyncMock(return_value=config)

        controller = _make_controller()
        request = _make_request(
            container=container, user=SimpleNamespace(roles=["superadmin"])
        )
        extra_context: dict = {}
        await controller._apply_tenant_context(request, extra_context)

        assert extra_context == {}

    @pytest.mark.asyncio
    async def test_noop_when_user_not_superadmin(self) -> None:
        from lexigram.admin.config import AdminConfig

        config = AdminConfig()
        config.tenancy.enabled = True
        container = MagicMock()
        container.resolve = AsyncMock(return_value=config)

        controller = _make_controller()
        request = _make_request(
            container=container, user=SimpleNamespace(roles=["editor"])
        )
        extra_context: dict = {}
        await controller._apply_tenant_context(request, extra_context)

        assert extra_context == {}

    @pytest.mark.asyncio
    async def test_populates_context_for_superadmin(self) -> None:
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.multitenancy.adapter import TenantProviderRegistry
        from lexigram.admin.multitenancy.models import TenantConfig

        config = AdminConfig()
        config.tenancy.enabled = True

        registry = TenantProviderRegistry()
        await registry.add(TenantConfig(tenant_id="acme", name="Acme Corp"))
        await registry.add(TenantConfig(tenant_id="globex", name="Globex Inc"))

        csrf_service = MagicMock()
        csrf_service.generate_token.return_value = "tok123"

        from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol

        async def resolve(cls: type) -> object:
            if cls is AdminConfig:
                return config
            if cls is TenantProviderRegistry:
                return registry
            if cls is AdminCsrfServiceProtocol:
                return csrf_service
            raise AssertionError(f"unexpected resolve({cls})")

        container = MagicMock()
        container.resolve = AsyncMock(side_effect=resolve)

        controller = _make_controller()
        request = _make_request(
            container=container,
            user=SimpleNamespace(roles=["superadmin"]),
            tenant_id="acme",
        )
        extra_context: dict = {}
        await controller._apply_tenant_context(request, extra_context)

        assert extra_context["current_tenant_id"] == "acme"
        assert extra_context["current_tenant_name"] == "Acme Corp"
        assert set(extra_context["tenant_list"]) == {
            ("acme", "Acme Corp"),
            ("globex", "Globex Inc"),
        }
        assert extra_context["tenant_csrf_token"] == "tok123"

    @pytest.mark.asyncio
    async def test_falls_back_to_raw_id_when_registry_has_no_match(self) -> None:
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.multitenancy.adapter import TenantProviderRegistry

        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()  # empty — no matching tenant

        from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol

        async def resolve(cls: type) -> object:
            if cls is AdminConfig:
                return config
            if cls is TenantProviderRegistry:
                return registry
            if cls is AdminCsrfServiceProtocol:
                raise RuntimeError("no csrf service in this test")
            raise AssertionError(f"unexpected resolve({cls})")

        container = MagicMock()
        container.resolve = AsyncMock(side_effect=resolve)

        controller = _make_controller()
        request = _make_request(
            container=container,
            user=SimpleNamespace(roles=["superadmin"]),
            tenant_id="deleted-tenant",
        )
        extra_context: dict = {}
        await controller._apply_tenant_context(request, extra_context)

        assert extra_context["current_tenant_id"] == "deleted-tenant"
        assert extra_context["current_tenant_name"] == "deleted-tenant"
        assert extra_context["tenant_list"] == []
        assert "tenant_csrf_token" not in extra_context
