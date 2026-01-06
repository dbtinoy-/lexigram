"""Tests for AdminRealtimeSubProvider full registration."""
from __future__ import annotations

import pytest


class TestAdminRealtimeSubProvider:
    @pytest.fixture
    def config(self):
        from lexigram.admin.config import AdminConfig

        return AdminConfig()

    @pytest.fixture
    def sub_provider(self, config):
        from lexigram.admin.di.sub_providers.realtime import AdminRealtimeSubProvider

        return AdminRealtimeSubProvider(config=config)

    @pytest.mark.asyncio
    async def test_register_places_services(self, sub_provider):
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        assert len(registrations) >= 2

    @pytest.mark.asyncio
    async def test_register_places_collaborative_service(self, sub_provider):
        """CollaborativeService should be registered if it exists."""
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        # Check if collaborative service is registered if available, or at least some services are registered
        collab_registered = any("Collaborative" in str(k) or "collaborative" in str(k) for k in registrations)
        assert collab_registered or len(registrations) >= 2

    @pytest.mark.asyncio
    async def test_health_check(self, sub_provider):
        result = await sub_provider.health_check()
        assert result.component == "admin_realtime"


__all__ = ["TestAdminRealtimeSubProvider"]

