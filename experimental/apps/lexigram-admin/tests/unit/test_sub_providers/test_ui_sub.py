"""Tests for AdminUISubProvider full registration."""
from __future__ import annotations

import pytest


class TestAdminUISubProvider:
    @pytest.fixture
    def config(self):
        from lexigram.admin.config import AdminConfig

        return AdminConfig()

    @pytest.fixture
    def sub_provider(self, config):
        from lexigram.admin.di.sub_providers.ui import AdminUISubProvider

        return AdminUISubProvider(config=config)

    @pytest.mark.asyncio
    async def test_register_places_component_registry(self, sub_provider):
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        from lexigram.admin.services.component_registry import ComponentRegistry

        assert ComponentRegistry in registrations

    @pytest.mark.asyncio
    async def test_register_places_navigation_assembler(self, sub_provider):
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        from lexigram.admin.navigation.assembler import NavigationAssembler

        assert NavigationAssembler in registrations

    @pytest.mark.asyncio
    async def test_health_check(self, sub_provider):
        result = await sub_provider.health_check()
        assert result.component == "admin_ui"


__all__ = ["TestAdminUISubProvider"]

