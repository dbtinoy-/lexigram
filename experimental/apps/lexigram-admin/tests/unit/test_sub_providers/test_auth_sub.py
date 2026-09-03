"""Tests for AdminAuthSubProvider full registration."""

from __future__ import annotations

import pytest


class TestAdminAuthSubProvider:
    @pytest.fixture
    def config(self):
        from lexigram.admin.config import AdminConfig

        return AdminConfig()

    @pytest.fixture
    def sub_provider(self, config):
        from lexigram.admin.di.sub_providers.auth import AdminAuthSubProvider

        return AdminAuthSubProvider(config=config)

    @pytest.mark.asyncio
    async def test_register_places_guard_chain(self, sub_provider):
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value=None, **kwargs):
                if "factory" in kwargs and kwargs["factory"] is not None:
                    registrations[key] = kwargs["factory"]
                else:
                    registrations[key] = value

        await sub_provider.register(FakeContainer())
        from lexigram.admin.auth.guard_chain import AdminGuardChain

        assert AdminGuardChain in registrations

    @pytest.mark.asyncio
    async def test_register_places_session_manager(self, sub_provider):
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value=None, **kwargs):
                if "factory" in kwargs and kwargs["factory"] is not None:
                    registrations[key] = kwargs["factory"]
                else:
                    registrations[key] = value

        await sub_provider.register(FakeContainer())
        from lexigram.admin.auth.session_manager import AdminSessionManager

        assert AdminSessionManager in registrations

    @pytest.mark.asyncio
    async def test_register_places_security_services(self, sub_provider):
        """Input sanitizer and security headers should be registered by auth sub-provider."""
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value=None, **kwargs):
                if "factory" in kwargs and kwargs["factory"] is not None:
                    registrations[key] = kwargs["factory"]
                else:
                    registrations[key] = value

        await sub_provider.register(FakeContainer())
        from lexigram.admin.middleware.input_sanitizer import AdminInputSanitizer
        from lexigram.admin.middleware.security_headers import AdminSecurityHeaders

        assert AdminInputSanitizer in registrations
        assert AdminSecurityHeaders in registrations

    @pytest.mark.asyncio
    async def test_csrf_service_uses_dedicated_token_lifetime(self):
        """AUTH-07: AdminCsrfService TTL follows csrf_token_lifetime, not idle_timeout."""
        from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol
        from lexigram.admin.auth.services.csrf_service import AdminCsrfService
        from lexigram.admin.config import AdminAuthConfig, AdminConfig
        from lexigram.admin.di.sub_providers.auth import AdminAuthSubProvider

        config = AdminConfig(
            auth=AdminAuthConfig(csrf_token_lifetime=7200, idle_timeout=14400)
        )
        sub_provider = AdminAuthSubProvider(config=config)

        registrations = {}

        class FakeContainer:
            def singleton(self, key, value=None, **kwargs):
                if "factory" in kwargs and kwargs["factory"] is not None:
                    registrations[key] = kwargs["factory"]
                else:
                    registrations[key] = value

        await sub_provider.register(FakeContainer())

        csrf = registrations[AdminCsrfServiceProtocol]
        assert isinstance(csrf, AdminCsrfService)
        assert csrf.token_lifetime_seconds == 7200

    @pytest.mark.asyncio
    async def test_csrf_service_default_lifetime(self, sub_provider):
        """AUTH-07: the default csrf_token_lifetime (3600) reaches the service."""
        from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol
        from lexigram.admin.auth.services.csrf_service import AdminCsrfService

        registrations = {}

        class FakeContainer:
            def singleton(self, key, value=None, **kwargs):
                if "factory" in kwargs and kwargs["factory"] is not None:
                    registrations[key] = kwargs["factory"]
                else:
                    registrations[key] = value

        await sub_provider.register(FakeContainer())

        csrf = registrations[AdminCsrfServiceProtocol]
        assert isinstance(csrf, AdminCsrfService)
        assert csrf.token_lifetime_seconds == 3600

    @pytest.mark.asyncio
    async def test_health_check(self, sub_provider):
        result = await sub_provider.health_check()
        assert result.component == "admin_auth"


class TestBootSchemaMarker:
    """Boot-loop matrix for the R15 schema-version marker."""

    @pytest.fixture
    def sub_provider(self):
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.di.sub_providers.auth import AdminAuthSubProvider

        return AdminAuthSubProvider(config=AdminConfig())

    def _make_world(self, monkeypatch, *, is_current, is_current_error=None):
        """Build fake stores, resolver, and a monkeypatched marker class."""
        from unittest.mock import AsyncMock

        class FakeStore:
            def __init__(self) -> None:
                self._initialized = False
                self.ensure_schema = AsyncMock()

        stores: dict[str, FakeStore] = {}

        class FakeResolver:
            async def resolve(self, token, *, bypass_visibility=False):
                name = getattr(token, "__name__", "")
                if name == "DatabaseProviderProtocol":
                    return object()
                if name.startswith("Admin") and name.endswith(
                    ("StoreProtocol",)
                ):
                    return stores.setdefault(name, FakeStore())
                raise RuntimeError(f"not registered: {name}")

        marker_calls: dict[str, object] = {"mark_current": None}

        class FakeMarker:
            def __init__(self, db) -> None:
                pass

            async def is_current(self, component, fingerprint):
                if is_current_error is not None:
                    raise is_current_error
                return is_current

            async def mark_current(self, component, fingerprint):
                marker_calls["mark_current"] = (component, fingerprint)

        monkeypatch.setattr(
            "lexigram.admin.auth.store.schema_marker.AdminSchemaMarker",
            FakeMarker,
        )
        return stores, FakeResolver(), marker_calls

    @pytest.mark.asyncio
    async def test_current_marker_skips_ensures_and_marks_ready(
        self, sub_provider, monkeypatch
    ):
        stores, resolver, marker_calls = self._make_world(
            monkeypatch, is_current=True
        )

        await sub_provider.boot(resolver)

        assert len(stores) == 8
        for store in stores.values():
            store.ensure_schema.assert_not_awaited()
            assert store._initialized is True
        assert marker_calls["mark_current"] is None

    @pytest.mark.asyncio
    async def test_stale_marker_runs_ensures_and_writes_marker(
        self, sub_provider, monkeypatch
    ):
        from lexigram.admin.auth.store.schema_marker import (
            ADMIN_AUTH_SCHEMA_FINGERPRINT,
            AUTH_STORES_COMPONENT,
        )

        stores, resolver, marker_calls = self._make_world(
            monkeypatch, is_current=False
        )

        await sub_provider.boot(resolver)

        assert len(stores) == 8
        for store in stores.values():
            store.ensure_schema.assert_awaited_once()
        assert marker_calls["mark_current"] == (
            AUTH_STORES_COMPONENT,
            ADMIN_AUTH_SCHEMA_FINGERPRINT,
        )

    @pytest.mark.asyncio
    async def test_failed_ensure_leaves_marker_unwritten(
        self, sub_provider, monkeypatch
    ):
        stores, resolver, marker_calls = self._make_world(
            monkeypatch, is_current=False
        )

        # Pre-seed one store whose ensure blows up.
        from unittest.mock import AsyncMock

        class BrokenStore:
            _initialized = False
            ensure_schema = AsyncMock(side_effect=RuntimeError("ddl failed"))

        stores["AdminMfaStoreProtocol"] = BrokenStore()

        await sub_provider.boot(resolver)

        assert marker_calls["mark_current"] is None

    @pytest.mark.asyncio
    async def test_marker_read_error_falls_back_to_ensures(
        self, sub_provider, monkeypatch
    ):
        stores, resolver, _ = self._make_world(
            monkeypatch, is_current=True, is_current_error=RuntimeError("db down")
        )

        await sub_provider.boot(resolver)

        assert len(stores) == 8
        for store in stores.values():
            store.ensure_schema.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_marker_class_import_failure_is_tolerated(
        self, sub_provider, monkeypatch
    ):
        stores, resolver, _ = self._make_world(monkeypatch, is_current=True)
        monkeypatch.setattr(
            "lexigram.admin.auth.store.schema_marker.AdminSchemaMarker",
            None,  # not callable → constructor raises TypeError
        )

        await sub_provider.boot(resolver)

        for store in stores.values():
            store.ensure_schema.assert_awaited_once()


__all__ = ["TestAdminAuthSubProvider", "TestBootSchemaMarker"]
