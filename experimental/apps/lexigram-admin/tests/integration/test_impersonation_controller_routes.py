"""Integration tests for POST /admin/impersonate/{user_id} and /stop."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware

from lexigram.admin.controllers.impersonation import ImpersonationController
from lexigram.admin.services.impersonation import ImpersonationService


async def _create_impersonation_app(*, actor_roles: list[str]) -> Starlette:
    service = ImpersonationService()
    user_store = MagicMock()
    user_store.get_user_by_id = AsyncMock(
        return_value=MagicMock(id="user-123", roles=["editor"])
    )
    controller = ImpersonationController(service=service, user_store=user_store)

    async def _inject_actor(request, call_next):
        request.state.user = MagicMock(id="admin1", roles=actor_roles)
        # Request.session is a read-only property backed by scope["session"]
        # (no setter) — set the scope key directly, not request.session.
        request.scope["session"] = {}
        return await call_next(request)

    app = Starlette(routes=controller.get_routes())
    app.add_middleware(BaseHTTPMiddleware, dispatch=_inject_actor)
    return app


class TestImpersonationRoutes:
    @pytest.mark.asyncio
    async def test_superadmin_start_returns_hx_redirect(self) -> None:
        app = await _create_impersonation_app(actor_roles=["superadmin"])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/impersonate/user-123")
        assert response.status_code == 200
        assert response.headers["HX-Redirect"] == "/admin/users"

    @pytest.mark.asyncio
    async def test_non_superadmin_start_returns_403(self) -> None:
        app = await _create_impersonation_app(actor_roles=["editor"])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/impersonate/user-123")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_stop_redirects(self) -> None:
        app = await _create_impersonation_app(actor_roles=["superadmin"])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/impersonate/stop", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/"

    @pytest.mark.asyncio
    async def test_stop_route_not_shadowed_by_parameterised_start_route(self) -> None:
        """Regression guard for the alphabetical route-ordering bug class:
        if get_routes() ever put the parameterised route first, this POST
        would be matched as user_id="stop" and return an HX-Redirect (200)
        instead of the real stop handler's 302."""
        app = await _create_impersonation_app(actor_roles=["superadmin"])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/impersonate/stop", follow_redirects=False)
        assert response.status_code == 302
        assert "HX-Redirect" not in response.headers
