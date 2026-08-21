"""Unit tests for TenancyController.set_tenant."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.config import AdminConfig
from lexigram.admin.controllers.tenancy import TenancyController
from lexigram.admin.multitenancy.adapter import TenantProviderRegistry
from lexigram.admin.multitenancy.models import TenantConfig


def _make_request(
    *, form: dict, user: SimpleNamespace | None, tenant_id: str | None = None
) -> MagicMock:
    request = MagicMock()
    request.state = SimpleNamespace(user=user, tenant_id=tenant_id)
    request.scope = {"admin_form_data": form}
    request.headers = {"referer": "/admin/dashboard"}
    request.client = SimpleNamespace(host="127.0.0.1")
    return request


class TestSetTenant:
    @pytest.mark.asyncio
    async def test_returns_404_when_tenancy_disabled(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = False
        controller = TenancyController(config=config, registry=None)
        request = _make_request(
            form={"tenant_id": "acme"}, user=SimpleNamespace(roles=["superadmin"])
        )

        response = await controller.set_tenant(request)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_403_for_non_superadmin(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()
        controller = TenancyController(config=config, registry=registry)
        request = _make_request(
            form={"tenant_id": "acme"}, user=SimpleNamespace(roles=["editor"])
        )

        response = await controller.set_tenant(request)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_400_for_unknown_tenant(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()
        controller = TenancyController(config=config, registry=registry)
        request = _make_request(
            form={"tenant_id": "nonexistent"},
            user=SimpleNamespace(roles=["superadmin"]),
        )

        response = await controller.set_tenant(request)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_400_for_missing_tenant_id(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()
        controller = TenancyController(config=config, registry=registry)
        request = _make_request(form={}, user=SimpleNamespace(roles=["superadmin"]))

        response = await controller.set_tenant(request)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_success_sets_cookie_and_redirects(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()
        await registry.add(TenantConfig(tenant_id="acme", name="Acme Corp"))
        controller = TenancyController(config=config, registry=registry)
        request = _make_request(
            form={"tenant_id": "acme"},
            user=SimpleNamespace(roles=["superadmin"]),
            tenant_id="default",
        )

        response = await controller.set_tenant(request)

        assert response.status_code == 303
        assert response.headers["location"] == "/admin/dashboard"
        set_cookie = response.headers.get("set-cookie", "")
        assert config.tenancy.cookie_name in set_cookie
        assert "acme" in set_cookie

    @pytest.mark.asyncio
    async def test_success_logs_audit_event(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()
        await registry.add(TenantConfig(tenant_id="acme", name="Acme Corp"))
        audit_service = MagicMock()
        audit_service.log_event = AsyncMock()
        controller = TenancyController(
            config=config, registry=registry, audit_service=audit_service
        )
        request = _make_request(
            form={"tenant_id": "acme"},
            user=SimpleNamespace(roles=["superadmin"]),
            tenant_id="default",
        )

        await controller.set_tenant(request)

        audit_service.log_event.assert_awaited_once()
        _, kwargs = audit_service.log_event.await_args
        from lexigram.admin.auth.types import AdminSecurityEventType

        assert kwargs["event_type"] == AdminSecurityEventType.TENANT_SWITCHED
        assert kwargs["success"] is True
        assert kwargs["metadata"] == {"from_tenant": "default", "to_tenant": "acme"}
