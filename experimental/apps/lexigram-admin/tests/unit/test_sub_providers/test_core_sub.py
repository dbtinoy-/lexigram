"""Tests for AdminCoreSubProvider full registration."""
from __future__ import annotations

import pytest


class TestAdminCoreSubProvider:
    @pytest.fixture
    def config(self):
        from lexigram.admin.config import AdminConfig

        return AdminConfig(title="Test Admin", prefix="/admin")

    @pytest.fixture
    def sub_provider(self, config):
        from lexigram.admin.di.sub_providers.core import AdminCoreSubProvider

        return AdminCoreSubProvider(config=config)

    @pytest.mark.asyncio
    async def test_register_places_config_in_container(self, sub_provider, config):
        """AdminConfig must be registered as singleton."""
        from lexigram.admin.config import AdminConfig

        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        assert AdminConfig in registrations
        assert registrations[AdminConfig] is config

    @pytest.mark.asyncio
    async def test_health_check_before_boot(self, sub_provider):
        result = await sub_provider.health_check()
        assert result.status.value == "unknown"

    @pytest.mark.asyncio
    async def test_health_check_after_boot(self, sub_provider):
        class FakeContainer:
            def singleton(self, key, value):
                pass

            async def resolve(self, key):
                return None

        await sub_provider.register(FakeContainer())
        await sub_provider.boot(FakeContainer())
        result = await sub_provider.health_check()
        assert result.status.value == "healthy"


__all__ = ["TestAdminCoreSubProvider"]

