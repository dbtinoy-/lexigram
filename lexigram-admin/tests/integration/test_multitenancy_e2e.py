"""End-to-end integration tests for admin multi-tenancy.

Spins up a minimal Starlette app with ``AdminTenantMiddleware`` and verifies
tenant resolution, 403 enforcement, public-path bypass, and cookie-based
resolution.
"""

from __future__ import annotations

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from lexigram.admin.config import TenancyConfig
from lexigram.admin.middleware.tenant import AdminTenantMiddleware


def _make_echo_app(tenancy: TenancyConfig) -> Starlette:
    """Return a Starlette app with tenant middleware and an echo route."""

    async def echo_tenant(request):
        tenant_id = getattr(request.state, "tenant_id", None)
        return JSONResponse({"tenant_id": tenant_id})

    async def public_page(request):
        return JSONResponse({"ok": True})

    app = Starlette(
        routes=[
            Route("/users", echo_tenant),
            Route("/login", public_page),
            Route("/health", public_page),
        ]
    )
    app.add_middleware(AdminTenantMiddleware, config=tenancy)
    return app


class TestMultiTenancyE2E:
    """E2E tests for the full admin tenant resolution pipeline."""

    @pytest.mark.asyncio
    async def test_403_when_tenant_missing_and_enabled(self) -> None:
        """Request without tenant info returns 403 when tenancy is enabled."""
        app = _make_echo_app(TenancyConfig(enabled=True))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://admin.test",
        ) as client:
            resp = await client.get("/users")
            assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_resolves_tenant_from_header(self) -> None:
        """X-Tenant-Id header resolves the tenant."""
        app = _make_echo_app(TenancyConfig(enabled=True))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://admin.test",
        ) as client:
            resp = await client.get("/users", headers={"x-tenant-id": "acme"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["tenant_id"] == "acme"

    @pytest.mark.asyncio
    async def test_resolves_tenant_from_cookie(self) -> None:
        """admin_tenant cookie resolves the tenant."""
        app = _make_echo_app(TenancyConfig(enabled=True))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://admin.test",
        ) as client:
            resp = await client.get("/users", cookies={"admin_tenant": "beta"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["tenant_id"] == "beta"

    @pytest.mark.asyncio
    async def test_header_overrides_cookie(self) -> None:
        """Header should take precedence over cookie."""
        app = _make_echo_app(TenancyConfig(enabled=True))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://admin.test",
        ) as client:
            resp = await client.get(
                "/users",
                headers={"x-tenant-id": "from-header"},
                cookies={"admin_tenant": "from-cookie"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["tenant_id"] == "from-header"

    @pytest.mark.asyncio
    async def test_public_path_bypasses_tenant_check(self) -> None:
        """Public paths like /login bypass tenant resolution."""
        app = _make_echo_app(TenancyConfig(enabled=True))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://admin.test",
        ) as client:
            resp = await client.get("/login")
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_health_path_bypasses_tenant_check(self) -> None:
        """Health check path bypasses tenant resolution."""
        app = _make_echo_app(TenancyConfig(enabled=True))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://admin.test",
        ) as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_disabled_allows_missing_tenant(self) -> None:
        """When tenancy is disabled, missing tenant returns empty string."""
        app = _make_echo_app(TenancyConfig(enabled=False))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://admin.test",
        ) as client:
            resp = await client.get("/users")
            assert resp.status_code == 200
            body = resp.json()
            assert body["tenant_id"] == ""

    @pytest.mark.asyncio
    async def test_disabled_still_resolves_tenant_from_header(self) -> None:
        """When tenancy is disabled, tenant is still resolved from header."""
        app = _make_echo_app(TenancyConfig(enabled=False))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://admin.test",
        ) as client:
            resp = await client.get("/users", headers={"x-tenant-id": "acme"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["tenant_id"] == "acme"
