"""Integration tests for POST /admin/set-tenant."""

from __future__ import annotations

from unittest.mock import MagicMock

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette
from starlette.routing import Route

from lexigram.admin.config import AdminConfig
from lexigram.admin.controllers.tenancy import TenancyController
from lexigram.admin.core.routing import AdminRouter
from lexigram.admin.multitenancy.adapter import TenantProviderRegistry
from lexigram.admin.multitenancy.models import TenantConfig


async def _create_tenancy_app(
    *, roles: list[str], tenants: list[TenantConfig] | None = None
) -> Starlette:
    config = AdminConfig()
    config.tenancy.enabled = True
    registry = TenantProviderRegistry()
    for tenant in tenants or []:
        await registry.add(tenant)
    controller = TenancyController(config=config, registry=registry)

    async def set_tenant_endpoint(request):
        request.state.user = MagicMock(roles=roles)
        request.state.tenant_id = "default"
        return await controller.set_tenant(request)

    return Starlette(
        routes=[Route("/admin/set-tenant", set_tenant_endpoint, methods=["POST"])]
    )


class TestSetTenantRoute:
    @pytest.mark.asyncio
    async def test_superadmin_switch_returns_303_and_sets_cookie(self) -> None:
        app = await _create_tenancy_app(
            roles=["superadmin"],
            tenants=[TenantConfig(tenant_id="acme", name="Acme Corp")],
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/admin/set-tenant",
                data={"tenant_id": "acme"},
                headers={"referer": "/admin/dashboard"},
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert "admin_tenant" in response.headers.get("set-cookie", "")

    @pytest.mark.asyncio
    async def test_non_superadmin_returns_403(self) -> None:
        app = await _create_tenancy_app(
            roles=["editor"],
            tenants=[TenantConfig(tenant_id="acme", name="Acme Corp")],
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/admin/set-tenant",
                data={"tenant_id": "acme"},
                follow_redirects=False,
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unknown_tenant_returns_400(self) -> None:
        app = await _create_tenancy_app(roles=["superadmin"], tenants=[])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/admin/set-tenant",
                data={"tenant_id": "nonexistent"},
                follow_redirects=False,
            )
        assert response.status_code == 400

    def test_get_routes_registers_set_tenant_post_route(self) -> None:
        """POST /admin/set-tenant is registered via the real AdminRouter path.

        Mirrors ``AdminRouter._build_routes``: controllers exposing
        ``get_routes()`` contribute their routes to the admin sub-app,
        which is mounted at ``config.prefix`` — so the deployed path is
        ``{prefix}`` + the route's mount-relative path.
        """
        config = AdminConfig(prefix="/admin")
        config.tenancy.enabled = True
        controller = TenancyController(config=config)

        routes = AdminRouter(config=config, controllers=[controller])._build_routes()

        set_tenant_routes = [
            route
            for route in routes
            if isinstance(route, Route)
            and route.path == "/set-tenant"
            and "POST" in route.methods
        ]
        assert len(set_tenant_routes) == 1
        route = set_tenant_routes[0]
        assert f"{config.prefix}{route.path}" == "/admin/set-tenant"
        assert route.endpoint == controller.set_tenant
