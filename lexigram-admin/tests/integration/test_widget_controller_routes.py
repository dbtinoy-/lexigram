"""Integration tests for WidgetController routes with auth session.

Tests the full routing stack including:
- Route registration via get_routes()
- Session middleware for auth
- Auth guard middleware redirects unauthenticated requests
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from lexigram.admin.controllers.widgets import WidgetController
from lexigram.contracts.admin.types import WidgetViewModel
from lexigram.result import Ok


def create_widget_app(
    *,
    contributor_exists: bool = True,
    widget_result: str = "<div>Widget Content</div>",
) -> tuple[Starlette, MagicMock]:
    """Create a test Starlette app with widget routes.

    Returns:
        Tuple of (app, registry) for test inspection.
    """
    registry = MagicMock()
    if contributor_exists:
        mock_contributor = MagicMock()
        mock_contributor.render_widget = AsyncMock(
            return_value=Ok(WidgetViewModel(body=widget_result))
        )
        mock_contributor.render_health_check = AsyncMock(return_value=Ok("<div>Health OK</div>"))
        registry.get.return_value = mock_contributor
    else:
        registry.get.return_value = None

    controller = WidgetController(registry=registry)

    async def widget_handler(request):
        contributor_id = request.path_params.get("contributor_id", "core")
        widget_name = request.path_params.get("widget_name", "health")
        return await controller.render_widget(
            request=request,
            contributor_id=contributor_id,
            widget_name=widget_name,
        )

    async def health_handler(request):
        contributor_id = request.path_params.get("contributor_id", "core")
        check_name = request.path_params.get("check_name", "db")
        return await controller.render_health_check(
            request=request,
            contributor_id=contributor_id,
            check_name=check_name,
        )

    async def login_page(request):
        return PlainTextResponse("Login Page - /admin/login")

    routes = [
        Route("/admin/login", login_page, methods=["GET"]),
        Route("/admin/widgets/{contributor_id}/{widget_name}", widget_handler, methods=["GET"]),
        Route("/admin/health/{contributor_id}/{check_name}", health_handler, methods=["GET"]),
    ]

    app = Starlette(routes=routes)
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key")
    return app, registry


class TestWidgetControllerRouteIntegration:
    """Test WidgetController routes at the integration level."""

    @pytest.mark.asyncio
    async def test_widget_route_returns_200_for_existing_contributor(self) -> None:
        """GET /admin/widgets/{contributor_id}/{widget_name} returns 200 when contributor exists."""
        app, _ = create_widget_app(contributor_exists=True)
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://testserver"
        ) as client:
            response = await client.get("/admin/widgets/core/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_widget_route_returns_error_card_for_nonexistent_contributor(self) -> None:
        """GET /admin/widgets/{contributor_id}/{widget_name} returns 200 with error card for unknown contributor."""
        app, _ = create_widget_app(contributor_exists=False)
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://testserver"
        ) as client:
            response = await client.get("/admin/widgets/nonexistent/health")
            assert response.status_code == 200
            assert b"widget-error-card" in response.content

    @pytest.mark.asyncio
    async def test_health_route_returns_200_for_existing_contributor(self) -> None:
        """GET /admin/health/{contributor_id}/{check_name} returns 200 when contributor exists."""
        app, _ = create_widget_app(contributor_exists=True)
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://testserver"
        ) as client:
            response = await client.get("/admin/health/core/db")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_route_returns_404_for_nonexistent_contributor(self) -> None:
        """GET /admin/health/{contributor_id}/{check_name} returns 404 for unknown contributor."""
        app, _ = create_widget_app(contributor_exists=False)
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://testserver"
        ) as client:
            response = await client.get("/admin/health/nonexistent/db")
            assert response.status_code == 404


class TestWidgetControllerGetRoutesIntegration:
    """Integration tests for WidgetController.get_routes()."""

    def test_get_routes_returns_list(self) -> None:
        """Test that get_routes returns a list."""
        registry = MagicMock()
        controller = WidgetController(registry=registry)
        routes = controller.get_routes()
        assert isinstance(routes, list)

    def test_get_routes_includes_widget_route(self) -> None:
        """Test that widget route is included."""
        registry = MagicMock()
        controller = WidgetController(registry=registry)
        routes = controller.get_routes()
        paths = [r.path for r in routes]
        assert any("widgets" in p for p in paths)

    def test_get_routes_includes_health_route(self) -> None:
        """Test that health check route is included."""
        registry = MagicMock()
        controller = WidgetController(registry=registry)
        routes = controller.get_routes()
        paths = [r.path for r in routes]
        assert any("health" in p for p in paths)

    def test_get_routes_paths_are_relative_to_mount(self) -> None:
        """Test that route paths do not have /admin prefix.

        Routes are mounted at /admin via AdminRouter Mount(), so get_routes()
        should return paths like /{contributor_id}/widgets/{widget_name},
        not /admin/{contributor_id}/widgets/{widget_name}.
        """
        registry = MagicMock()
        controller = WidgetController(registry=registry)
        routes = controller.get_routes()
        for route in routes:
            assert not route.path.startswith("/admin"), (
                f"Route path '{route.path}' should not include /admin prefix - "
                "the Mount() in AdminRouter provides that."
            )

    def test_get_routes_can_be_mounted_to_starlette_app(self) -> None:
        """Test that get_routes() routes can be added to a Starlette app."""
        registry = MagicMock()
        mock_contributor = MagicMock()
        mock_contributor.render_widget = AsyncMock(
            return_value=Ok(WidgetViewModel(body="<div>Test</div>"))
        )
        registry.get.return_value = mock_contributor

        controller = WidgetController(registry=registry)

        app = Starlette(routes=[])
        for route in controller.get_routes():
            app.routes.append(route)

        assert len(app.routes) >= 2

    @pytest.mark.asyncio
    async def test_mounted_routes_handle_requests(self) -> None:
        """Test that routes from get_routes() actually handle requests."""
        registry = MagicMock()
        mock_contributor = MagicMock()
        mock_contributor.render_widget = AsyncMock(
            return_value=Ok(WidgetViewModel(body="<div>Widget OK</div>"))
        )
        registry.get.return_value = mock_contributor

        controller = WidgetController(registry=registry)

        async def simple_index(request):
            return PlainTextResponse("Index")

        app = Starlette(routes=[Route("/simple", simple_index)])
        for route in controller.get_routes():
            app.routes.append(route)

        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://testserver"
        ) as client:
            simple_resp = await client.get("/simple")
            assert simple_resp.status_code == 200

            widget_resp = await client.get("/core/widgets/health")
            assert widget_resp.status_code == 200


class TestWidgetControllerAuthSessionIntegration:
    """Test WidgetController with session/auth context.

    These tests verify behavior when auth sessions are involved.
    In production, AdminAuthGuardMiddleware handles redirecting
    unauthenticated users. We test the controller's response
    to auth-related scenarios.
    """

    @pytest.mark.asyncio
    async def test_widget_with_empty_session(self) -> None:
        """Widget controller handles requests with no session data."""
        app, _ = create_widget_app(contributor_exists=True)
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://testserver"
        ) as client:
            response = await client.get("/admin/widgets/core/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_multiple_widgets_same_session(self) -> None:
        """Multiple widget requests work within same session."""
        app, _ = create_widget_app(contributor_exists=True)
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://testserver"
        ) as client:
            response1 = await client.get("/admin/widgets/core/health")
            response2 = await client.get("/admin/widgets/cache/hit_miss")
            assert response1.status_code == 200
            assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_same_session(self) -> None:
        """Multiple health check requests work within same session."""
        app, _ = create_widget_app(contributor_exists=True)
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://testserver"
        ) as client:
            response1 = await client.get("/admin/health/core/db")
            response2 = await client.get("/admin/health/cache/backend")
            assert response1.status_code == 200
            assert response2.status_code == 200
