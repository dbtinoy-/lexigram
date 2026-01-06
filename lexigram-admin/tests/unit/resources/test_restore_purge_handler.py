"""Tests for RestoreActionHandler, PurgeActionHandler, and route registration.

Verifies that the restore/purge action dispatchers and resource routing
are properly wired for the soft-delete feature.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.admin.config import AdminConfig
from lexigram.admin.core.routing import AdminRouter
from lexigram.admin.resources.handler import PurgeActionHandler, RestoreActionHandler


class TestRestoreActionHandler:
    """Tests for RestoreActionHandler."""

    def test_can_handle_restore(self) -> None:
        handler = RestoreActionHandler()
        assert handler.can_handle("restore") is True

    def test_cannot_handle_other(self) -> None:
        handler = RestoreActionHandler()
        assert handler.can_handle("edit") is False

    def test_cannot_handle_empty(self) -> None:
        handler = RestoreActionHandler()
        assert handler.can_handle("") is False


class TestPurgeActionHandler:
    """Tests for PurgeActionHandler."""

    def test_can_handle_purge(self) -> None:
        handler = PurgeActionHandler()
        assert handler.can_handle("purge") is True

    def test_cannot_handle_other(self) -> None:
        handler = PurgeActionHandler()
        assert handler.can_handle("delete") is False

    def test_cannot_handle_empty(self) -> None:
        handler = PurgeActionHandler()
        assert handler.can_handle("") is False


class TestRestorePurgeRouteRegistration:
    """Tests for restore/purge route registration in AdminRouter."""

    def test_restore_route_in_build_resource_routes(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)
        paths = [r.path for r in routes]
        assert any("/restore" in path for path in paths), (
            f"No route with '/restore' found in paths: {paths}"
        )

    def test_purge_route_in_build_resource_routes(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)
        paths = [r.path for r in routes]
        assert any("/purge" in path for path in paths), (
            f"No route with '/purge' found in paths: {paths}"
        )

    def test_restore_purge_routes_use_get_method(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)
        restore_routes = [r for r in routes if "/restore" in (r.path or "")]
        purge_routes = [r for r in routes if "/purge" in (r.path or "")]
        for route in restore_routes + purge_routes:
            if hasattr(route, "methods") and route.methods is not None:
                assert "GET" in route.methods

    def test_routes_for_multiple_resources(self) -> None:
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

        assert any("/restore" in p for p in users_paths)
        assert any("/purge" in p for p in users_paths)
        assert any("/restore" in p for p in posts_paths)
        assert any("/purge" in p for p in posts_paths)
