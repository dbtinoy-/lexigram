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


__all__ = ["TestAdminAuthSubProvider"]
