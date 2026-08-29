"""Tests for refactored standalone AdminRegistry."""
from __future__ import annotations


class TestAdminRegistryRefactored:
    def test_registry_standalone_no_args(self):
        from lexigram.admin.core.registry import AdminRegistry
        registry = AdminRegistry()
        assert registry._resources == {}
        assert registry._controllers == []

    def test_register_resource(self):
        from lexigram.admin.core.registry import AdminRegistry
        registry = AdminRegistry()
        class FakeResource:
            name = "test"
            cluster = None
        registry.register_resource(FakeResource)
        # Class registration is deferred — check _deferred_resources
        assert "test" in registry._deferred_resources

    def test_register_controller(self):
        from lexigram.admin.core.registry import AdminRegistry
        registry = AdminRegistry()
        class FakeController:
            pass
        registry.register_controller(FakeController)
        assert FakeController in registry.controllers

    def test_methods_return_self(self):
        from lexigram.admin.core.registry import AdminRegistry
        registry = AdminRegistry()
        class FakeResource:
            name = "items"
            cluster = None
        result = registry.register_resource(FakeResource)
        assert result is registry
