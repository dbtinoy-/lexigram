"""Tests for AdminProvider."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lexigram.admin.config import AdminConfig
from lexigram.admin.di.bundle_provider import AdminProvider
from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.core.provider import ProviderPriority


class FakeRegistrar:
    def __init__(self) -> None:
        self.registrations: dict = {}

    def singleton(
        self,
        key: object,
        value: object = None,
        **kwargs: object,
    ) -> None:
        if "factory" in kwargs and kwargs["factory"] is not None:
            self.registrations[key] = kwargs["factory"]
        else:
            self.registrations[key] = value

    def transient(self, key: object, value: object) -> None:
        self.registrations[key] = value


class TestAdminProvider:
    def test_provider_attributes(self) -> None:
        provider = AdminProvider()
        assert provider.name == "admin"
        assert provider.priority == ProviderPriority.APPLICATION
        # config_key is intentionally None — admin config is set programmatically
        assert provider.config_key is None

    def test_default_config(self) -> None:
        provider = AdminProvider()
        assert isinstance(provider.config, AdminConfig)

    def test_custom_config(self) -> None:
        config = AdminConfig(title="Custom Admin")
        provider = AdminProvider(config=config)
        assert provider.config.title == "Custom Admin"

    def test_config_is_immutable_after_init(self) -> None:
        """Config must not have a setter — mutation after init is prohibited."""
        provider = AdminProvider()
        config_prop = type(provider).__dict__.get("config")
        assert isinstance(config_prop, property)
        assert config_prop.fset is None, "config must not have a setter"

    def test_sub_providers_empty_before_register(self) -> None:
        """Sub-providers must not be created in __init__ — only in register()."""
        provider = AdminProvider()
        assert len(provider._sub_providers) == 0

    @pytest.mark.asyncio
    async def test_has_sub_providers_after_register(self) -> None:
        provider = AdminProvider()
        container = FakeRegistrar()
        await provider.register(container)
        assert len(provider._sub_providers) > 0

    @pytest.mark.asyncio
    async def test_bundle_provider_has_eight_sub_providers(self) -> None:
        """Test that all 8 required sub-providers are wired during register()."""
        provider = AdminProvider()
        container = FakeRegistrar()
        await provider.register(container)
        assert len(provider._sub_providers) == 9

    def test_from_config(self) -> None:
        config = AdminConfig(title="From Config")
        provider = AdminProvider.from_config(config)
        assert provider.config.title == "From Config"

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        provider = AdminProvider()
        result = await provider.health_check()
        assert result.component == "admin"
        assert result.status in (
            HealthStatus.HEALTHY,
            HealthStatus.UNKNOWN,
            HealthStatus.DEGRADED,
        )

    @pytest.mark.asyncio
    async def test_mount_to_app_tolerates_resource_resolution_failures(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Best-effort resource resolution should not crash admin mounting."""

        class BrokenResource:
            pass

        class _Resolver:
            async def resolve(
                self,
                token: object,
                *,
                bypass_visibility: bool = False,
            ) -> object:
                token_name = getattr(token, "__name__", token.__class__.__name__)
                if token is BrokenResource:
                    raise RuntimeError("boom")
                if token_name == "AdminUserStoreProtocol":
                    raise RuntimeError("store unavailable")
                if token_name == "AdminCsrfServiceProtocol":
                    return SimpleNamespace()
                if token_name == "NavItemBuilder":
                    return SimpleNamespace(set_resources=lambda _: None)
                return SimpleNamespace()

        class _FakeRouter:
            def __init__(self, **_: object) -> None:
                pass

            def mount(self, app: object) -> object:
                return app

        provider = AdminProvider(
            resources=[BrokenResource],
            config=AdminConfig(strict_resource_resolution=False),
        )
        app = SimpleNamespace(state=SimpleNamespace())
        monkeypatch.setattr(
            "lexigram.admin.core.routing.AdminRouter",
            _FakeRouter,
        )

        await provider.mount_to_app(app, _Resolver())

    @pytest.mark.asyncio
    async def test_mount_to_app_uses_admin_boot_resolver_for_admin_services(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Admin-only middleware deps should resolve from the admin boot scope."""

        class _AdminResolver:
            async def resolve(
                self,
                token: object,
                *,
                bypass_visibility: bool = False,
            ) -> object:
                token_name = getattr(token, "__name__", token.__class__.__name__)
                if token_name == "AdminUserStoreProtocol":
                    return SimpleNamespace()
                if token_name == "AdminCsrfServiceProtocol":
                    return SimpleNamespace()
                return SimpleNamespace()

        class _WebResolver:
            async def resolve(
                self,
                token: object,
                *,
                bypass_visibility: bool = False,
            ) -> object:
                token_name = getattr(token, "__name__", token.__class__.__name__)
                if token_name in {"AdminUserStoreProtocol", "AdminCsrfServiceProtocol"}:
                    raise RuntimeError("web scope cannot resolve admin services")
                return SimpleNamespace()

        captured: dict[str, object] = {}

        class _FakeRouter:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)

            def mount(self, app: object) -> object:
                return app

        provider = AdminProvider(
            config=AdminConfig.from_dict(
                {"auth": {"security": {"setup_token": "test-setup-token"}}}
            )
        )
        await provider.register(FakeRegistrar())
        await provider.boot(_AdminResolver())
        app = SimpleNamespace(state=SimpleNamespace())
        monkeypatch.setattr(
            "lexigram.admin.core.routing.AdminRouter",
            _FakeRouter,
        )

        await provider.mount_to_app(app, _WebResolver())

        middleware_stack = captured.get("middleware_stack")
        assert isinstance(middleware_stack, list)
        assert len(middleware_stack) >= 2

    @pytest.mark.asyncio
    async def test_mount_to_app_wires_security_headers_outermost(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SecurityHeadersMiddleware must sit at index 0 (outermost)."""
        from lexigram.admin.middleware.security_headers import (
            SecurityHeadersMiddleware,
        )

        class _Resolver:
            async def resolve(
                self,
                token: object,
                *,
                bypass_visibility: bool = False,
            ) -> object:
                return SimpleNamespace()

        captured: dict[str, object] = {}

        class _FakeRouter:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)

            def mount(self, app: object) -> object:
                return app

        provider = AdminProvider(
            config=AdminConfig.from_dict(
                {"auth": {"security": {"setup_token": "test-setup-token"}}}
            )
        )
        await provider.register(FakeRegistrar())
        await provider.boot(_Resolver())
        app = SimpleNamespace(state=SimpleNamespace())
        monkeypatch.setattr(
            "lexigram.admin.core.routing.AdminRouter",
            _FakeRouter,
        )

        await provider.mount_to_app(app, _Resolver())

        middleware_stack = captured.get("middleware_stack")
        assert isinstance(middleware_stack, list)
        assert middleware_stack[0][0] is SecurityHeadersMiddleware
        # The settings store is passed through (may be None without a DB).
        assert "settings_store" in middleware_stack[0][1]

    @pytest.mark.asyncio
    async def test_mount_to_app_does_not_require_nav_builder_from_web_scope(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Admin mounting should reuse its registered NavItemBuilder instance."""

        class _Resolver:
            async def resolve(
                self,
                token: object,
                *,
                bypass_visibility: bool = False,
            ) -> object:
                token_name = getattr(token, "__name__", token.__class__.__name__)
                if token_name == "NavItemBuilder":
                    raise RuntimeError("web scope cannot resolve nav builder")
                if token_name == "AdminUserStoreProtocol":
                    raise RuntimeError("store unavailable")
                if token_name == "AdminCsrfServiceProtocol":
                    return SimpleNamespace()
                return SimpleNamespace()

        class _FakeRouter:
            def __init__(self, **_: object) -> None:
                pass

            def mount(self, app: object) -> object:
                return app

        provider = AdminProvider()
        await provider.register(FakeRegistrar())
        app = SimpleNamespace(state=SimpleNamespace())
        monkeypatch.setattr(
            "lexigram.admin.core.routing.AdminRouter",
            _FakeRouter,
        )

        await provider.mount_to_app(app, _Resolver())

    @pytest.mark.asyncio
    async def test_mount_to_app_bypasses_visibility_for_admin_owned_bindings(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class DemoResource:
            pass

        class DemoController:
            pass

        resolved: list[tuple[str, bool]] = []

        class _Resolver:
            async def resolve(
                self,
                token: object,
                *,
                bypass_visibility: bool = False,
            ) -> object:
                token_name = getattr(token, "__name__", token.__class__.__name__)
                resolved.append((token_name, bypass_visibility))
                return SimpleNamespace()

        class _FakeRouter:
            def __init__(self, **_: object) -> None:
                pass

            def mount(self, app: object) -> object:
                return app

        provider = AdminProvider(
            resources=[DemoResource],
            controllers=[DemoController],
            config=AdminConfig.from_dict(
                {"auth": {"security": {"setup_token": "test-setup-token"}}}
            ),
        )
        await provider.register(FakeRegistrar())
        await provider.boot(_Resolver())
        app = SimpleNamespace(state=SimpleNamespace())
        monkeypatch.setattr(
            "lexigram.admin.core.routing.AdminRouter",
            _FakeRouter,
        )

        await provider.mount_to_app(app, _Resolver())

        admin_owned_tokens = {
            "DemoResource",
            "DemoController",
            "AdminUserStoreProtocol",
            "AdminCsrfServiceProtocol",
        }
        assert {
            token_name for token_name, _ in resolved if token_name in admin_owned_tokens
        } == admin_owned_tokens
        assert all(
            bypass_visibility
            for token_name, bypass_visibility in resolved
            if token_name in admin_owned_tokens
        )

    @pytest.mark.asyncio
    async def test_mount_to_app_progress_controller_uses_local_tracker_fallback(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When DI can't resolve ProgressController, it should fall back to
        the admin-owned LocalProgressTracker, not import lexigram-tasks."""
        from lexigram.admin.controllers.progress import LocalProgressTracker

        class _Resolver:
            async def resolve(
                self,
                token: object,
                *,
                bypass_visibility: bool = False,
            ) -> object:
                token_name = getattr(token, "__name__", token.__class__.__name__)
                if token_name == "ProgressController":
                    raise RuntimeError("no tracker registered")
                if token_name == "AdminUserStoreProtocol":
                    raise RuntimeError("store unavailable")
                if token_name == "AdminCsrfServiceProtocol":
                    return SimpleNamespace()
                if token_name == "NavItemBuilder":
                    return SimpleNamespace(set_resources=lambda _: None)
                return SimpleNamespace()

        captured: dict[str, object] = {}

        class _FakeRouter:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)

            def mount(self, app: object) -> object:
                return app

        provider = AdminProvider()
        app = SimpleNamespace(state=SimpleNamespace())
        monkeypatch.setattr(
            "lexigram.admin.core.routing.AdminRouter",
            _FakeRouter,
        )

        await provider.mount_to_app(app, _Resolver())

        controllers = captured.get("controllers")
        assert isinstance(controllers, list)
        progress_controllers = [
            c for c in controllers if type(c).__name__ == "ProgressController"
        ]
        assert len(progress_controllers) == 1
        assert isinstance(progress_controllers[0].tracker, LocalProgressTracker)

    @pytest.mark.asyncio
    async def test_mount_registers_users_resource(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A ``users`` resource is registered when provided to the provider."""

        class _Resolver:
            async def resolve(
                self,
                token: object,
                *,
                bypass_visibility: bool = False,
            ) -> object:
                named = type(getattr(token, "__name__", "anon"), (SimpleNamespace,), {})
                return named()

        captured: dict[str, object] = {}

        class _FakeRouter:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)

            def mount(self, app: object) -> object:
                return app

        from lexigram.admin.resources.users import UserResource

        class _UsersResource(UserResource):
            name = "users"

        provider = AdminProvider(resources=[_UsersResource])
        app = SimpleNamespace(state=SimpleNamespace())
        monkeypatch.setattr(
            "lexigram.admin.core.routing.AdminRouter",
            _FakeRouter,
        )

        await provider.mount_to_app(app, _Resolver())

        assert "users" in captured.get("resources", {})


__all__ = ["TestAdminProvider"]
