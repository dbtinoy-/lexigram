"""Tests for CloneActionHandler and clone route registration.

Verifies that the clone action dispatcher and resource routing
are properly wired for the clone feature.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.admin.config import AdminConfig
from lexigram.admin.core.routing import AdminRouter
from lexigram.admin.resources.action_handlers import CloneActionHandler


class TestCloneActionHandler:
    """Tests for CloneActionHandler."""

    def test_can_handle_clone(self) -> None:
        handler = CloneActionHandler()
        assert handler.can_handle("clone") is True

    def test_cannot_handle_other(self) -> None:
        handler = CloneActionHandler()
        assert handler.can_handle("edit") is False
        assert handler.can_handle("create") is False
        assert handler.can_handle("list") is False

    def test_cannot_handle_empty(self) -> None:
        handler = CloneActionHandler()
        assert handler.can_handle("") is False


class TestCloneRouteRegistration:
    """Tests for clone route registration in AdminRouter."""

    def test_clone_route_in_build_resource_routes(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)
        paths = [r.path for r in routes]
        assert any("/clone" in path for path in paths), (
            f"No route with '/clone' found in paths: {paths}"
        )

    def test_clone_route_for_multiple_resources(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_users = MagicMock()
        mock_users.relations = []
        mock_posts = MagicMock()
        mock_posts.relations = []

        router = AdminRouter(
            config=config,
            resources={"users": mock_users, "posts": mock_posts},
        )

        users_routes = router._build_resource_routes("users", mock_users)
        posts_routes = router._build_resource_routes("posts", mock_posts)

        users_paths = [r.path for r in users_routes]
        posts_paths = [r.path for r in posts_routes]

        assert any("/clone" in p for p in users_paths)
        assert any("/clone" in p for p in posts_paths)

    def test_clone_route_requires_post(self) -> None:
        """Clone must not be triggerable by a safe browser GET."""
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)
        clone_routes = [r for r in routes if "/clone" in (r.path or "")]
        assert clone_routes
        for route in clone_routes:
            assert route.methods == {"POST"}

    def test_inline_mutation_routes_are_registered(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)

        field_route = next(r for r in routes if "/field/" in (r.path or ""))
        inline_route = next(r for r in routes if r.path == "/users/{id}/inline")
        inline_page_route = next(
            r for r in routes if r.path == "/users/{id}/inline-edit"
        )

        assert {"GET", "POST"}.issubset(field_route.methods or set())
        assert {"GET", "PATCH"}.issubset(inline_route.methods or set())
        assert {"GET"}.issubset(inline_page_route.methods or set())
