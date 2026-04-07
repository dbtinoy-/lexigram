"""Tests for CloneActionHandler and clone route registration.

Verifies that the clone action dispatcher and resource routing
are properly wired for the clone feature.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.admin.config import AdminConfig
from lexigram.admin.core.routing import AdminRouter
from lexigram.admin.resources.handler import CloneActionHandler


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

    def test_clone_route_uses_get_method(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)
        clone_routes = [r for r in routes if "/clone" in (r.path or "")]
        for route in clone_routes:
            if hasattr(route, "methods") and route.methods is not None:
                assert "GET" in route.methods
