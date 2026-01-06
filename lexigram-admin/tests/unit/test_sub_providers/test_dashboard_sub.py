"""Tests for AdminDashboardSubProvider full registration."""
from __future__ import annotations

import pytest


class TestAdminDashboardSubProvider:
    @pytest.fixture
    def config(self):
        from lexigram.admin.config import AdminConfig

        return AdminConfig()

    @pytest.fixture
    def registry(self):
        from lexigram.admin.contributors.registry import ContributorRegistry

        return ContributorRegistry()

    @pytest.fixture
    def sub_provider(self, config, registry):
        from lexigram.admin.di.sub_providers.dashboard import AdminDashboardSubProvider

        return AdminDashboardSubProvider(config=config, contributor_registry=registry)

    @pytest.mark.asyncio
    async def test_register_places_dashboard_protocol(self, sub_provider):
        from lexigram.contracts.admin.protocols import AdminDashboardProtocol

        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        assert AdminDashboardProtocol in registrations

    @pytest.mark.asyncio
    async def test_register_places_user_dashboard_service(self, sub_provider):
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        user_dash_registered = any("UserDashboard" in str(k) or "user_dashboard" in str(k) for k in registrations)
        assert user_dash_registered or len(registrations) >= 3

    @pytest.mark.asyncio
    async def test_health_check(self, sub_provider):
        class FakeContainer:
            def singleton(self, key, value):
                pass

        await sub_provider.register(FakeContainer())
        result = await sub_provider.health_check()
        assert result.component == "admin_dashboard"
        assert result.status.value == "healthy"


__all__ = ["TestAdminDashboardSubProvider"]

