"""Tests for refactored AdminRouter."""
from __future__ import annotations
import pytest


class TestAdminRouterRefactored:
    def test_admin_router_accepts_config(self):
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.core.routing import AdminRouter
        config = AdminConfig(prefix="/admin")
        router = AdminRouter(config=config)
        assert router._config.prefix == "/admin"

    def test_admin_router_stores_resources(self):
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.core.routing import AdminRouter
        config = AdminConfig(prefix="/admin")
        router = AdminRouter(config=config, resources={"test": object()})
        assert "test" in router._resources

    def test_admin_router_no_provider(self):
        """AdminRouter should not take AdminProvider as constructor arg."""
        import inspect
        from lexigram.admin.core.routing import AdminRouter
        sig = inspect.signature(AdminRouter.__init__)
        assert "provider" not in sig.parameters


class TestRelationOptionsRoute:
    def test_relation_options_route_before_id_catchall(self):
        """The fixed relation-options path must precede the {id} catch-all."""
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.core.routing import AdminRouter

        router = AdminRouter(config=AdminConfig(prefix="/admin"))
        routes = router._build_resource_routes("categories", object())
        paths = [route.path for route in routes]
        assert "/categories/relation-options" in paths
        assert paths.index("/categories/relation-options") < paths.index(
            "/categories/{id}"
        )
        options_route = next(
            route
            for route in routes
            if route.path == "/categories/relation-options"
        )
        assert "GET" in options_route.methods
