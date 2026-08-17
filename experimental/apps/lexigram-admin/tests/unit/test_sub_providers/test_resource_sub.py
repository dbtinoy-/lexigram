"""Tests for AdminResourceSubProvider full registration."""
from __future__ import annotations

import pytest


class TestAdminResourceSubProvider:
    @pytest.fixture
    def config(self):
        from lexigram.admin.config import AdminConfig

        return AdminConfig()

    @pytest.fixture
    def sub_provider(self, config):
        from lexigram.admin.di.sub_providers.resource import AdminResourceSubProvider

        return AdminResourceSubProvider(config=config, resources=[])

    @pytest.mark.asyncio
    async def test_register_places_services(self, sub_provider):
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        assert len(registrations) >= 1

    @pytest.mark.asyncio
    async def test_resource_count_in_health(self):
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.di.sub_providers.resource import AdminResourceSubProvider

        class FakeResource:
            pass

        sp = AdminResourceSubProvider(config=AdminConfig(), resources=[FakeResource, FakeResource])

        class FakeContainer:
            def singleton(self, key, value):
                pass

            async def resolve(self, key):
                return None

        await sp.register(FakeContainer())
        await sp.boot(FakeContainer())
        result = await sp.health_check()
        assert "2 registered" in result.message

    @pytest.mark.asyncio
    async def test_health_check_component_name(self, sub_provider):
        result = await sub_provider.health_check()
        assert result.component == "admin_resource"


__all__ = ["TestAdminResourceSubProvider"]

