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
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        from lexigram.admin.auth.guard_chain import AdminGuardChain

        assert AdminGuardChain in registrations

    @pytest.mark.asyncio
    async def test_register_places_session_manager(self, sub_provider):
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        from lexigram.admin.auth.session_manager import AdminSessionManager

        assert AdminSessionManager in registrations

    @pytest.mark.asyncio
    async def test_register_places_security_services(self, sub_provider):
        """Input sanitizer and security headers should be registered by auth sub-provider."""
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        from lexigram.admin.middleware.input_sanitizer import AdminInputSanitizer
        from lexigram.admin.middleware.security_headers import AdminSecurityHeaders

        assert AdminInputSanitizer in registrations
        assert AdminSecurityHeaders in registrations

    @pytest.mark.asyncio
    async def test_health_check(self, sub_provider):
        result = await sub_provider.health_check()
        assert result.component == "admin_auth"


__all__ = ["TestAdminAuthSubProvider"]

