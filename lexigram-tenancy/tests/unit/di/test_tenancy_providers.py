"""Tests for tenancy providers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.tenancy.protocols import TenantProviderProtocol
from lexigram.tenancy.config import (
    ConfigOverridesConfig,
    IntegrationConfig,
    LifecycleConfig,
    ResolutionConfig,
    TenancyConfig,
)
from lexigram.tenancy.di.config_provider import TenantConfigProvider
from lexigram.tenancy.di.integration_provider import TenantIntegrationProvider
from lexigram.tenancy.di.lifecycle_provider import TenantLifecycleProvider
from lexigram.tenancy.di.provider import TenancyProvider
from lexigram.tenancy.di.resolution_provider import TenantResolutionProvider


class TestTenancyProvider:
    """Tests for TenancyProvider bundle provider."""

    @pytest.fixture
    def config(self) -> TenancyConfig:
        """Create a test configuration."""
        return TenancyConfig()

    @pytest.fixture
    def provider(self, config: TenancyConfig) -> TenancyProvider:
        """Create the TenancyProvider instance."""
        return TenancyProvider(config)

    def test_name(self, provider: TenancyProvider) -> None:
        """Provider has correct name."""
        assert provider.name == "tenancy"

    def test_priority_is_infrastructure(self, provider: TenancyProvider) -> None:
        """Provider has INFRASTRUCTURE priority."""
        from lexigram.contracts.core.provider import ProviderPriority

        assert provider.priority == ProviderPriority.INFRASTRUCTURE

    def test_sub_providers_count(self, provider: TenancyProvider) -> None:
        """Bundle provider manages five sub-providers."""
        assert len(provider._sub_providers) == 5

    def test_sub_provider_names(self, provider: TenancyProvider) -> None:
        """Sub-providers have expected names."""
        names = [sp.name for sp in provider._sub_providers]
        assert "tenant_resolution" in names
        assert "tenant_lifecycle" in names
        assert "tenant_config" in names
        assert "tenant_migration" in names
        assert "tenant_integration" in names

    @pytest.mark.asyncio
    async def test_register_delegates_to_sub_providers(self, provider: TenancyProvider) -> None:
        """register() delegates to all sub-providers."""
        container = MagicMock()
        for sp in provider._sub_providers:
            sp.register = AsyncMock()

        await provider.register(container)

        for sp in provider._sub_providers:
            sp.register.assert_called_once_with(container)

    @pytest.mark.asyncio
    async def test_boot_delegates_to_sub_providers(self, provider: TenancyProvider) -> None:
        """boot() delegates to all sub-providers."""
        container = MagicMock()
        for sp in provider._sub_providers:
            sp.boot = AsyncMock()

        await provider.boot(container)

        for sp in provider._sub_providers:
            sp.boot.assert_called_once_with(container)

    @pytest.mark.asyncio
    async def test_shutdown_calls_all_sub_providers(self, provider: TenancyProvider) -> None:
        """shutdown() calls all sub-providers."""
        for sp in provider._sub_providers:
            sp.shutdown = AsyncMock()

        await provider.shutdown()

        # Verify all sub-providers had shutdown called
        for sp in provider._sub_providers:
            sp.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, provider: TenancyProvider) -> None:
        """health_check() returns HEALTHY status."""
        result = await provider.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.component == "tenancy"

    @pytest.mark.asyncio
    async def test_health_check_includes_sub_provider_names(self, provider: TenancyProvider) -> None:
        """health_check() includes sub-provider names in details."""
        result = await provider.health_check()

        assert "sub_providers" in result.details
        names = result.details["sub_providers"]
        assert "tenant_resolution" in names
        assert "tenant_lifecycle" in names


class TestTenantResolutionProvider:
    """Tests for TenantResolutionProvider."""

    @pytest.fixture
    def config(self) -> ResolutionConfig:
        """Create a test resolution config."""
        return ResolutionConfig(
            resolvers=["header"],
            header_name="X-Tenant-ID",
        )

    @pytest.fixture
    def provider(self, config: ResolutionConfig) -> TenantResolutionProvider:
        """Create the provider instance."""
        return TenantResolutionProvider(config)

    def test_name(self, provider: TenantResolutionProvider) -> None:
        """Provider has correct name."""
        assert provider.name == "tenant_resolution"

    @pytest.mark.asyncio
    async def test_register_creates_resolver_registry(self, provider: TenantResolutionProvider) -> None:
        """register() creates and binds ResolverRegistry."""
        container = MagicMock()

        await provider.register(container)

        container.singleton.assert_called()

    @pytest.mark.asyncio
    async def test_boot_wires_validator(self, provider: TenantResolutionProvider) -> None:
        """boot() wires TenantValidator."""
        container = MagicMock()
        # Mock container.resolve returns appropriate mocks
        mock_provider = MagicMock()

        async def resolve_mock(key):
            if key.__name__ == "TenantProviderProtocol":
                return mock_provider
            if key.__name__ == "CompositeResolver":
                return MagicMock()
            return MagicMock()

        container.resolve = AsyncMock(side_effect=resolve_mock)

        await provider.boot(container)

        # Should have called resolve for TenantProviderProtocol
        container.resolve.assert_called()

    @pytest.mark.asyncio
    async def test_shutdown_is_noop(self, provider: TenantResolutionProvider) -> None:
        """shutdown() is a no-op."""
        await provider.shutdown()


class TestTenantLifecycleProvider:
    """Tests for TenantLifecycleProvider."""

    @pytest.fixture
    def config(self) -> LifecycleConfig:
        """Create a test lifecycle config."""
        return LifecycleConfig(
            isolation_strategy="row_level",
            auto_provision_isolation=True,
        )

    @pytest.fixture
    def provider(self, config: LifecycleConfig) -> TenantLifecycleProvider:
        """Create the provider instance."""
        return TenantLifecycleProvider(config)

    def test_name(self, provider: TenantLifecycleProvider) -> None:
        """Provider has correct name."""
        assert provider.name == "tenant_lifecycle"

    @pytest.mark.asyncio
    async def test_register_binds_tenant_store(self, provider: TenantLifecycleProvider) -> None:
        """register() binds InMemoryTenantProvider."""
        container = MagicMock()

        await provider.register(container)

        # Should have called singleton twice (TenantProviderProtocol and InMemoryTenantProvider)
        assert container.singleton.call_count >= 2

    @pytest.mark.asyncio
    async def test_register_binds_isolation_registry(self, provider: TenantLifecycleProvider) -> None:
        """register() binds IsolationStrategyRegistry."""
        container = MagicMock()

        await provider.register(container)

        # Verify IsolationStrategyRegistry was bound
        calls = container.singleton.call_args_list
        assert any(
            "IsolationStrategyRegistry" in str(call)
            for call in calls
        )

    @pytest.mark.asyncio
    async def test_boot_wires_provisioner(self, provider: TenantLifecycleProvider) -> None:
        """boot() wires TenantProvisioner."""
        container = MagicMock()
        container.resolve = AsyncMock(
            side_effect=[
                MagicMock(),  # IsolationStrategyRegistry
                MagicMock(),  # TenantProviderProtocol
                MagicMock(),  # TenantValidator
            ]
        )

        await provider.boot(container)

        container.singleton.assert_called()

    @pytest.mark.asyncio
    async def test_boot_wires_lifecycle_service(self, provider: TenantLifecycleProvider) -> None:
        """boot() wires TenantLifecycleService."""
        container = MagicMock()
        container.resolve = AsyncMock(
            side_effect=[
                MagicMock(),  # IsolationStrategyRegistry
                MagicMock(),  # TenantProviderProtocol
                MagicMock(),  # TenantValidator
            ]
        )

        await provider.boot(container)

        # Should have called singleton for TenantLifecycleService
        calls = container.singleton.call_args_list
        assert any("TenantLifecycleService" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_shutdown_is_noop(self, provider: TenantLifecycleProvider) -> None:
        """shutdown() is a no-op."""
        await provider.shutdown()


class TestTenantConfigProvider:
    """Tests for TenantConfigProvider."""

    @pytest.fixture
    def config(self) -> ConfigOverridesConfig:
        """Create a test config overrides config."""
        return ConfigOverridesConfig(
            cache_ttl=300,
        )

    @pytest.fixture
    def provider(self, config: ConfigOverridesConfig) -> TenantConfigProvider:
        """Create the provider instance."""
        return TenantConfigProvider(config)

    def test_name(self, provider: TenantConfigProvider) -> None:
        """Provider has correct name."""
        assert provider.name == "tenant_config"

    @pytest.mark.asyncio
    async def test_boot_wires_cached_config_provider(self, provider: TenantConfigProvider) -> None:
        """boot() wires CachedTenantConfigProvider."""
        container = MagicMock()
        mock_store = MagicMock()
        container.resolve = AsyncMock(
            side_effect=[
                mock_store,  # InMemoryTenantProvider
            ]
        )

        await provider.boot(container)

        container.singleton.assert_called()

    @pytest.mark.asyncio
    async def test_boot_wires_config_service(self, provider: TenantConfigProvider) -> None:
        """boot() wires TenantConfigService."""
        container = MagicMock()
        mock_store = MagicMock()
        container.resolve = AsyncMock(
            side_effect=[
                mock_store,  # InMemoryTenantProvider
            ]
        )

        await provider.boot(container)

        # Should have called singleton for TenantConfigService
        calls = container.singleton.call_args_list
        assert any("TenantConfigService" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_shutdown_is_noop(self, provider: TenantConfigProvider) -> None:
        """shutdown() is a no-op."""
        await provider.shutdown()


class TestTenantIntegrationProvider:
    """Tests for TenantIntegrationProvider."""

    @pytest.fixture
    def config_enabled(self) -> IntegrationConfig:
        """Create config with features enabled."""
        return IntegrationConfig(
            cache_key_prefix="tenant:",
            sql_context_bridge=True,
        )

    @pytest.fixture
    def config_disabled(self) -> IntegrationConfig:
        """Create config with features disabled."""
        return IntegrationConfig(
            cache_key_prefix=None,
            sql_context_bridge=False,
        )

    @pytest.fixture
    def provider_enabled(
        self, config_enabled: IntegrationConfig
    ) -> TenantIntegrationProvider:
        """Create provider with features enabled."""
        return TenantIntegrationProvider(config_enabled)

    @pytest.fixture
    def provider_disabled(
        self, config_disabled: IntegrationConfig
    ) -> TenantIntegrationProvider:
        """Create provider with features disabled."""
        return TenantIntegrationProvider(config_disabled)

    def test_name(self, provider_enabled: TenantIntegrationProvider) -> None:
        """Provider has correct name."""
        assert provider_enabled.name == "tenant_integration"

    @pytest.mark.asyncio
    async def test_register_is_noop(self, provider_enabled: TenantIntegrationProvider) -> None:
        """register() is a no-op."""
        container = MagicMock()
        await provider_enabled.register(container)
        # No calls should be made
        container.assert_not_called()

    @pytest.mark.asyncio
    async def test_boot_skips_when_disabled(
        self, provider_disabled: TenantIntegrationProvider
    ) -> None:
        """boot() does nothing when features are disabled."""
        container = MagicMock()
        await provider_disabled.boot(container)
        # Should not raise, no resolution attempts

    @pytest.mark.asyncio
    async def test_shutdown_is_noop(self, provider_enabled: TenantIntegrationProvider) -> None:
        """shutdown() is a no-op."""
        await provider_enabled.shutdown()