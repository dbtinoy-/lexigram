"""Tests for legacy controller and Page coexistence via AdminRouter."""

from __future__ import annotations

from typing import Any

from starlette.routing import Mount, Route

from lexigram.admin.config import AdminConfig
from lexigram.admin.core.routing import AdminRouter
from lexigram.admin.pages.base import Page
from lexigram.admin.pages.types import PageResponse


class _LegacyController:
    """Simulates a legacy-style controller with get_routes()."""

    def get_routes(self) -> list[Route]:
        return [
            Route(
                "/legacy/dashboard",
                endpoint=self.dashboard,
                methods=["GET"],
                name="legacy_dashboard",
            ),
            Route(
                "/legacy/stats",
                endpoint=self.stats,
                methods=["GET"],
                name="legacy_stats",
            ),
        ]

    async def dashboard(self, request: Any) -> str:
        return "Dashboard"

    async def stats(self, request: Any) -> str:
        return "Stats"


class _DashboardPage(Page):
    title = "Dashboard"
    path = "/pages/dashboard"

    async def view(self, request: Any) -> PageResponse:
        return PageResponse(content="<h1>Dashboard</h1>", title=self.title)


class _SettingsPage(Page):
    title = "Settings"
    path = "/pages/settings"

    async def view(self, request: Any) -> PageResponse:
        return PageResponse(content="<h1>Settings</h1>", title=self.title)


class _NoPathPage(Page):
    title = "Analytics"

    async def view(self, request: Any) -> PageResponse:
        return PageResponse(content="<h1>Analytics</h1>", title=self.title)


def _register_page(router: AdminRouter, page: Page) -> None:
    """Register a Page as an extra route on the AdminRouter."""
    path = page.path or f"/{page.title.lower()}"
    router.add_route(
        path=path,
        method="GET",
        handler=page.view,
        name=f"page_{page.title.lower()}",
    )


def _filter_user_routes(routes: list[Route]) -> list[Route]:
    """Return only user-registered Route objects, skipping Mounts and built-in endpoints."""
    built_in = {"admin_search", "admin_command_palette", "admin_openapi"}
    return [r for r in routes if isinstance(r, Route) and r.name not in built_in]


class TestControllerPageCoexistence:
    """Verify legacy controller and Page routes coexist through AdminRouter."""

    def test_controller_and_page_routes_coexist(self) -> None:
        """Both controller routes and page routes appear in the same route list."""
        config = AdminConfig(prefix="/admin")
        controller = _LegacyController()
        router = AdminRouter(config=config, controllers=[controller])
        _register_page(router, _DashboardPage())

        routes = _filter_user_routes(router._build_routes())
        paths = {r.path for r in routes}

        assert "/legacy/dashboard" in paths
        assert "/legacy/stats" in paths
        assert "/pages/dashboard" in paths

    def test_controller_routes_have_get_method(self) -> None:
        """Controller routes are registered with GET method."""
        config = AdminConfig(prefix="/admin")
        controller = _LegacyController()
        router = AdminRouter(config=config, controllers=[controller])
        _register_page(router, _DashboardPage())

        routes = _filter_user_routes(router._build_routes())
        for route in routes:
            assert "GET" in route.methods

    def test_page_routes_serve_get(self) -> None:
        """Page routes are registered as GET."""
        config = AdminConfig(prefix="/admin")
        controller = _LegacyController()
        router = AdminRouter(config=config, controllers=[controller])
        _register_page(router, _DashboardPage())
        _register_page(router, _SettingsPage())

        routes = _filter_user_routes(router._build_routes())
        page_routes = [r for r in routes if "/pages/" in r.path]
        assert len(page_routes) == 2
        for route in page_routes:
            assert "GET" in route.methods

    def test_no_route_collision_between_controllers_and_pages(self) -> None:
        """Routes from controllers and pages with different paths don't collide."""
        config = AdminConfig(prefix="/admin")
        controller = _LegacyController()
        router = AdminRouter(config=config, controllers=[controller])
        _register_page(router, _DashboardPage())
        _register_page(router, _SettingsPage())

        routes = _filter_user_routes(router._build_routes())
        paths = [r.path for r in routes]
        assert len(paths) == len(set(paths))

    def test_route_uniqueness_by_path_and_method(self) -> None:
        """Every (path, method) pair is unique across sources."""
        config = AdminConfig(prefix="/admin")
        controller = _LegacyController()
        router = AdminRouter(config=config, controllers=[controller])
        _register_page(router, _DashboardPage())
        _register_page(router, _SettingsPage())

        routes = _filter_user_routes(router._build_routes())
        route_keys = {(r.path, tuple(sorted(r.methods))) for r in routes}
        assert len(route_keys) == len(routes)

    def test_page_without_path_gets_sensible_default(self) -> None:
        """A Page that doesn't declare path gets a default derived from its title."""
        page = _NoPathPage()
        assert page.path == ""

        default_path = page.path or f"/{page.title.lower()}"
        assert default_path == "/analytics"

    def test_controller_endpoints_are_callable(self) -> None:
        """Controller route endpoints are callable functions."""
        controller = _LegacyController()
        for route in controller.get_routes():
            assert callable(route.endpoint)

    def test_page_view_is_callable(self) -> None:
        """Page view method is callable for use as route handler."""
        page = _DashboardPage()
        assert callable(page.view)

    def test_multiple_pages_registered_with_distinct_paths(self) -> None:
        """Multiple pages with distinct paths produce unique routes."""
        config = AdminConfig(prefix="/admin")
        controller = _LegacyController()
        router = AdminRouter(config=config, controllers=[controller])
        _register_page(router, _DashboardPage())
        _register_page(router, _SettingsPage())
        _register_page(router, _NoPathPage())

        routes = _filter_user_routes(router._build_routes())
        paths = [r.path for r in routes]
        assert len(paths) == len(set(paths))
