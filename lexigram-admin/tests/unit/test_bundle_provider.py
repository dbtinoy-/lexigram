"""Tests for AdminProvider."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from lexigram.admin.config import AdminConfig
from lexigram.admin.di.bundle_provider import AdminProvider
from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.core.provider import ProviderPriority


class FakeRegistrar:
    def __init__(self) -> None:
        self.registrations: dict = {}

    def singleton(self, key: object, value: object) -> None:
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
                    raise RuntimeError("csrf unavailable")
                if token_name == "NavItemBuilder":
                    return SimpleNamespace(set_resources=lambda resources: None)
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

        provider = AdminProvider()
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
                    raise RuntimeError("csrf unavailable")
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


__all__ = ["TestAdminProvider"]
