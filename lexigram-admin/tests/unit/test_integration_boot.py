"""Integration tests for the full AdminProvider boot lifecycle.

Verifies that all 7 sub-providers register/boot/shutdown without error
and that the provider API no longer depends on the legacy AdminProvider.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def config():
    from lexigram.admin.config import AdminConfig

    return AdminConfig(prefix="/admin", title="Test Admin")


@pytest.fixture
def provider(config):
    from lexigram.admin.di.bundle_provider import AdminProvider

    return AdminProvider(config=config)


class FakeRegistrar:
    def __init__(self):
        self.registrations: dict = {}

    def singleton(self, key, value):
        self.registrations[key] = value

    def transient(self, key, value):
        self.registrations[key] = value


class FakeResolver:
    def singleton(self, key, value):
        pass

    def transient(self, key, value):
        pass

    async def resolve(self, key, **kwargs):
        return None


class TestAdminProviderBootLifecycle:
    """Integration tests for the full AdminProvider boot lifecycle."""

    def test_provider_instantiates_with_config(self, provider, config):
        """AdminProvider should instantiate with AdminConfig."""
        assert provider._config is config

    @pytest.mark.asyncio
    async def test_provider_has_eight_sub_providers(self, provider):
        """AdminProvider should wire all 8 sub-providers during register()."""
        assert hasattr(provider, "_sub_providers")
        # Sub-providers are empty until register() is called
        assert len(provider._sub_providers) == 0
        container = FakeRegistrar()
        await provider.register(container)
        assert len(provider._sub_providers) == 9

    @pytest.mark.asyncio
    async def test_register_all_sub_providers(self, provider):
        """All 7 sub-providers should register without error."""
        container = FakeRegistrar()
        await provider.register(container)
        # Should have registered at minimum core services
        assert len(container.registrations) >= 1

    @pytest.mark.asyncio
    async def test_boot_all_sub_providers(self, provider):
        """All 7 sub-providers should boot without error."""
        registrar = FakeRegistrar()
        resolver = FakeResolver()
        await provider.register(registrar)
        await provider.boot(resolver)

    @pytest.mark.asyncio
    async def test_health_check_aggregation(self, provider):
        """Health check should aggregate across all sub-providers."""
        registrar = FakeRegistrar()
        resolver = FakeResolver()
        await provider.register(registrar)
        await provider.boot(resolver)
        result = await provider.health_check()
        assert result.component == "admin"
        assert result.details is not None
        assert len(result.details) == 9

    @pytest.mark.asyncio
    async def test_shutdown_proceeds_without_error(self, provider):
        """Shutdown should proceed without error."""
        registrar = FakeRegistrar()
        resolver = FakeResolver()
        await provider.register(registrar)
        await provider.boot(resolver)
        await provider.shutdown()

    def test_admin_provider_can_be_imported_from_canonical_location(self):
        """AdminProvider can be imported from the canonical location."""
        from lexigram.admin.di.bundle_provider import AdminProvider

        assert AdminProvider is not None

    def test_no_god_class_methods_on_provider(self, provider):
        """Provider should not have old god-class methods."""
        god_class_methods = [
            "build_nav_items",
            "build_system_menu_items",
            "render_html_shell",
            "register_resource",
            "register_controller",
            "register_command",
        ]
        for method in god_class_methods:
            assert not hasattr(provider, method), (
                f"AdminProvider should not have god-class method: {method}"
            )

    def test_admin_bundle_provider_accepts_resources_and_controllers(self, config):
        """AdminProvider should accept resources and controllers in constructor."""
        from lexigram.admin.di.bundle_provider import AdminProvider

        class FakeResource:
            name = "test"

        class FakeController:
            pass

        provider = AdminProvider(
            config=config,
            resources=[FakeResource],
            controllers=[FakeController],
        )
        assert FakeResource in provider._resources
        assert FakeController in provider._controllers
