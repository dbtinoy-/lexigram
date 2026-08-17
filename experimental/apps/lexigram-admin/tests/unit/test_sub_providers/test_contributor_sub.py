"""Tests for AdminContributorSubProvider."""
from __future__ import annotations

import pytest


class TestAdminContributorSubProvider:
    @pytest.fixture
    def config(self):
        from lexigram.admin.config import AdminConfig

        return AdminConfig()

    @pytest.fixture
    def sub_provider(self, config):
        from lexigram.admin.di.sub_providers.contributor import AdminContributorSubProvider

        return AdminContributorSubProvider(config=config)

    def test_core_contributor_registered_on_init(self, sub_provider):
        """CoreAdminContributor should be registered automatically."""
        core = sub_provider.registry.get("core")
        assert core is not None

    @pytest.mark.asyncio
    async def test_register_places_registry_in_container(self, sub_provider):
        from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol

        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        assert AdminContributorRegistryProtocol in registrations

    @pytest.mark.asyncio
    async def test_health_check_reports_count(self, sub_provider):
        result = sub_provider.health_check()
        assert "contributor" in result.message
        assert result.details is not None
        assert result.details["count"] >= 1

    def test_disabled_contributor_not_loaded(self):
        from lexigram.admin.config import AdminConfig, ContributorConfig
        from lexigram.admin.di.sub_providers.contributor import AdminContributorSubProvider

        config = AdminConfig(contributors={"some_plugin": ContributorConfig(enabled=False)})
        sp = AdminContributorSubProvider(config=config)
        assert sp._is_enabled("some_plugin") is False
        assert sp._is_enabled("core") is True


__all__ = ["TestAdminContributorSubProvider"]

