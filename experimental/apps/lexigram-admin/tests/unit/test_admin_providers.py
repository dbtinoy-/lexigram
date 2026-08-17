"""Unit tests for admin DI providers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from lexigram.admin.di.sub_providers.core import AdminCoreSubProvider
from lexigram.admin.di.sub_providers.contributor import AdminContributorSubProvider


class TestAdminCoreSubProvider:
    """Tests for AdminCoreSubProvider."""

    @pytest.fixture
    def mock_config(self) -> MagicMock:
        config = MagicMock()
        config.prefix = "/admin"
        config.title = "Admin"
        return config

    @pytest.fixture
    def mock_container(self) -> MagicMock:
        container = MagicMock()
        container.singleton = AsyncMock()
        return container

    @pytest.mark.asyncio
    async def test_constructor_stores_config(
        self, mock_config: MagicMock
    ) -> None:
        """Test that constructor stores the config."""
        provider = AdminCoreSubProvider(config=mock_config)
        assert provider.config is mock_config

    @pytest.mark.asyncio
    async def test_register_singletons(
        self, mock_config: MagicMock, mock_container: MagicMock
    ) -> None:
        """Test that register binds core services."""
        provider = AdminCoreSubProvider(config=mock_config)
        await provider.register(mock_container)

        assert mock_container.singleton.call_count >= 4

    @pytest.mark.asyncio
    async def test_boot_sets_mounted_flag(
        self, mock_config: MagicMock, mock_container: MagicMock
    ) -> None:
        """Test that boot marks provider as mounted."""
        provider = AdminCoreSubProvider(config=mock_config)
        await provider.boot(mock_container)

        assert provider._mounted is True

    @pytest.mark.asyncio
    async def test_shutdown_clears_mounted_flag(
        self, mock_config: MagicMock
    ) -> None:
        """Test that shutdown clears mounted flag."""
        provider = AdminCoreSubProvider(config=mock_config)
        provider._mounted = True

        await provider.shutdown()

        assert provider._mounted is False

    @pytest.mark.asyncio
    async def test_health_check_healthy_when_mounted(
        self, mock_config: MagicMock
    ) -> None:
        """Test health check returns HEALTHY when mounted."""
        provider = AdminCoreSubProvider(config=mock_config)
        provider._mounted = True

        result = await provider.health_check()

        assert result.status.value == "healthy"
        assert result.component == "admin_core"

    @pytest.mark.asyncio
    async def test_health_check_unknown_when_not_mounted(
        self, mock_config: MagicMock
    ) -> None:
        """Test health check returns UNKNOWN when not mounted."""
        provider = AdminCoreSubProvider(config=mock_config)
        provider._mounted = False

        result = await provider.health_check()

        assert result.status.value == "unknown"


class TestAdminContributorSubProvider:
    """Tests for AdminContributorSubProvider."""

    @pytest.fixture
    def mock_config(self) -> MagicMock:
        config = MagicMock()
        config.contributors = {}
        return config

    @pytest.fixture
    def mock_container(self) -> MagicMock:
        container = MagicMock()
        container.singleton = AsyncMock()
        return container

    @pytest.fixture
    def mock_contributor(self) -> MagicMock:
        contributor = MagicMock()
        contributor.name = "test_contributor"
        contributor.contributor_id = "test-id"
        contributor.on_admin_boot = AsyncMock()
        contributor.on_admin_shutdown = AsyncMock()
        return contributor

    @pytest.mark.asyncio
    async def test_constructor_initializes_registry(self) -> None:
        """Test that constructor initializes an empty registry."""
        provider = AdminContributorSubProvider()

        assert provider.registry is not None
        assert provider.config is None

    @pytest.mark.asyncio
    async def test_constructor_accepts_config(
        self, mock_config: MagicMock
    ) -> None:
        """Test that constructor accepts config."""
        provider = AdminContributorSubProvider(config=mock_config)

        assert provider.config is mock_config

    @pytest.mark.asyncio
    async def test_register_binds_registry(
        self, mock_config: MagicMock, mock_container: MagicMock
    ) -> None:
        """Test that register binds the contributor registry."""
        from lexigram.admin.contributors.registry import ContributorRegistry
        from lexigram.contracts.admin.protocols import (
            AdminContributorRegistryProtocol,
        )

        provider = AdminContributorSubProvider(config=mock_config)
        await provider.register(mock_container)

        calls = mock_container.singleton.call_args_list
        protocol_bound = any(
            arg[0] is AdminContributorRegistryProtocol
            or arg[0] is ContributorRegistry
            for call in calls
            for arg in [call[0]]
            if call
        )
        assert protocol_bound

    @pytest.mark.asyncio
    async def test_boot_calls_contributor_on_admin_boot(
        self,
        mock_config: MagicMock,
        mock_contributor: MagicMock,
    ) -> None:
        """Test that boot calls on_admin_boot on contributors."""
        provider = AdminContributorSubProvider(
            config=mock_config, contributors=[mock_contributor]
        )
        await provider.boot_all()

        mock_contributor.on_admin_boot.assert_called_once()

    @pytest.mark.asyncio
    async def test_boot_continues_on_contributor_failure(
        self, mock_config: MagicMock
    ) -> None:
        """Test that boot continues when a contributor fails."""
        bad_contributor = MagicMock()
        bad_contributor.name = "bad"
        bad_contributor.on_admin_boot = AsyncMock(
            side_effect=Exception("boot failed")
        )
        bad_contributor.contributor_id = "bad-id"

        good_contributor = MagicMock()
        good_contributor.name = "good"
        good_contributor.on_admin_boot = AsyncMock()
        good_contributor.contributor_id = "good-id"

        provider = AdminContributorSubProvider(
            config=mock_config,
            contributors=[bad_contributor, good_contributor],
        )
        await provider.boot_all()

        good_contributor.on_admin_boot.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_iterates_registry_contributors(
        self,
        mock_config: MagicMock,
    ) -> None:
        """Test that shutdown iterates registry contributors without error."""
        provider = AdminContributorSubProvider(config=mock_config)

        await provider.shutdown()

        assert provider._registry is not None

    @pytest.mark.asyncio
    async def test_health_check_healthy_with_no_failures(
        self, mock_config: MagicMock
    ) -> None:
        """Test health check returns HEALTHY when no boot failures."""
        provider = AdminContributorSubProvider(config=mock_config)

        result = provider.health_check()

        assert result.status.value == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded_with_failures(
        self, mock_config: MagicMock, mock_contributor: MagicMock
    ) -> None:
        """Test health check returns DEGRADED when boot failures exist."""
        provider = AdminContributorSubProvider(
            config=mock_config, contributors=[mock_contributor]
        )
        provider._boot_failures["bad-id"] = "something failed"

        result = provider.health_check()

        assert result.status.value == "degraded"
        assert "bad-id" in result.details["boot_failures"]

    @pytest.mark.asyncio
    async def test_boot_all_tracks_failures(
        self, mock_config: MagicMock, mock_contributor: MagicMock
    ) -> None:
        """Test that boot_all tracks failures."""
        mock_contributor.on_admin_boot = AsyncMock(
            side_effect=Exception("fail")
        )

        provider = AdminContributorSubProvider(
            config=mock_config, contributors=[mock_contributor]
        )
        await provider.boot_all()

        assert mock_contributor.contributor_id in provider._boot_failures

    @pytest.mark.asyncio
    async def test_is_enabled_returns_true_with_no_config(self) -> None:
        """Test is_enabled returns True when no config."""
        provider = AdminContributorSubProvider()

        assert provider._is_enabled("any") is True

    @pytest.mark.asyncio
    async def test_is_enabled_respects_config(
        self, mock_config: MagicMock
    ) -> None:
        """Test is_enabled respects config enabled flag."""
        mock_config.contributors = {"test": {"enabled": False}}

        provider = AdminContributorSubProvider(config=mock_config)

        assert provider._is_enabled("test") is False

    @pytest.mark.asyncio
    async def test_is_enabled_defaults_to_true(
        self, mock_config: MagicMock
    ) -> None:
        """Test is_enabled defaults to True for unknown contributors."""
        mock_config.contributors = {}

        provider = AdminContributorSubProvider(config=mock_config)

        assert provider._is_enabled("unknown") is True


class TestAdminProviderImports:
    """Test that admin providers can be imported."""

    def test_admin_bundle_provider_import(self) -> None:
        """Test AdminProvider can be imported."""
        from lexigram.admin.di.bundle_provider import AdminProvider

        assert AdminProvider is not None

    def test_admin_provider_alias_import(self) -> None:
        """Test AdminProvider alias can be imported."""
        from lexigram.admin.di.bundle_provider import AdminProvider

        assert AdminProvider is not None
        assert AdminProvider is not None

    def test_core_sub_provider_import(self) -> None:
        """Test AdminCoreSubProvider can be imported."""
        from lexigram.admin.di.sub_providers.core import AdminCoreSubProvider

        assert AdminCoreSubProvider is not None

    def test_contributor_sub_provider_import(self) -> None:
        """Test AdminContributorSubProvider can be imported."""
        from lexigram.admin.di.sub_providers.contributor import (
            AdminContributorSubProvider,
        )

        assert AdminContributorSubProvider is not None


class TestProviderProperties:
    """Test provider properties and attributes."""

    def test_admin_bundle_provider_has_name(self) -> None:
        """Test AdminProvider has correct name."""
        from lexigram.admin.di.bundle_provider import AdminProvider
        from lexigram.contracts.core.provider import ProviderPriority

        provider = AdminProvider()

        assert provider.name == "admin"
        assert provider.priority == ProviderPriority.APPLICATION