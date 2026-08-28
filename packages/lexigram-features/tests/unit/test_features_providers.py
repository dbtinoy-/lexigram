"""Tests for feature flag providers."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.contracts.core.health import HealthStatus
from lexigram.features.backends.base import AbstractFlagProvider
from lexigram.features.backends.local import LocalProvider
from lexigram.features.config import FeatureFlagsConfig
from lexigram.features.di.provider import FeatureFlagsProvider
from lexigram.features.exceptions import FlagNotFoundError
from lexigram.features.types import Flag, FlagContext, FlagEvaluation, FlagType
from lexigram.features.manager.flag_manager import FlagManager


class TestAbstractFlagProvider:
    """Tests for AbstractFlagProvider abstract base class."""

    @pytest.fixture
    def provider(self) -> AbstractFlagProvider:
        """Create a concrete test provider."""

        class TestProvider(AbstractFlagProvider):
            async def get_flag_definition(self, name: str) -> Flag | None:
                return self._flags.get(name)

            async def get_all_flags(self) -> dict[str, Flag]:
                return self._flags.copy()

            def __init__(self, flags: dict[str, Flag]) -> None:
                super().__init__()
                self._flags = flags

        return TestProvider({
            "bool_enabled": Flag("bool_enabled", type=FlagType.BOOLEAN, enabled=True),
            "bool_disabled": Flag("bool_disabled", type=FlagType.BOOLEAN, enabled=False),
            "percentage_50": Flag(
                "percentage_50",
                type=FlagType.PERCENTAGE,
                enabled=True,
                percentage=50,
            ),
            "user_list": Flag(
                "user_list",
                type=FlagType.USER_LIST,
                enabled=True,
                user_list=["user-1", "user-2"],
            ),
            "time_based": Flag(
                "time_based",
                type=FlagType.TIME_BASED,
                enabled=True,
            ),
            "variant": Flag(
                "variant",
                type=FlagType.VARIANT,
                enabled=True,
                variants={"a": 50, "b": 50},
                default_variant="a",
            ),
        })

    @pytest.mark.asyncio
    async def test_evaluate_boolean_enabled(self, provider: AbstractFlagProvider) -> None:
        """Test boolean flag evaluation when enabled."""
        result = await provider.evaluate("bool_enabled")
        assert result.enabled is True
        assert result.value is True
        assert result.reason == "boolean"

    @pytest.mark.asyncio
    async def test_evaluate_boolean_disabled(self, provider: AbstractFlagProvider) -> None:
        """Test boolean flag evaluation when disabled."""
        result = await provider.evaluate("bool_disabled")
        assert result.enabled is False
        assert result.value is False
        assert result.reason == "flag_disabled"

    @pytest.mark.asyncio
    async def test_evaluate_not_found(self, provider: AbstractFlagProvider) -> None:
        """Test evaluation of non-existent flag."""
        result = await provider.evaluate("nonexistent")
        assert result.enabled is False
        assert result.reason == "flag_not_found"

    @pytest.mark.asyncio
    async def test_evaluate_with_context(self, provider: AbstractFlagProvider) -> None:
        """Test evaluation with context."""
        context = FlagContext(user_id="test-user")
        result = await provider.evaluate("bool_enabled", context)
        assert result.enabled is True

    @pytest.mark.asyncio
    async def test_get_flag_returns_default_for_missing(
        self,
        provider: AbstractFlagProvider,
    ) -> None:
        """Test get_flag returns default when flag not found."""
        result = await provider.get_flag("nonexistent", default=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_flag_returns_evaluated_value(
        self,
        provider: AbstractFlagProvider,
    ) -> None:
        """Test get_flag returns evaluated value."""
        result = await provider.get_flag("bool_enabled")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_variant_returns_default_for_missing(
        self,
        provider: AbstractFlagProvider,
    ) -> None:
        """Test get_variant returns default when flag not found."""
        result = await provider.get_variant("nonexistent", default="default_value")
        assert result == "default_value"

    @pytest.mark.asyncio
    async def test_get_variant_returns_variant_value(
        self,
        provider: AbstractFlagProvider,
    ) -> None:
        """Test get_variant returns variant value."""
        result = await provider.get_variant("variant")
        assert result in ("a", "b")

    def test_evaluate_sync_raises_not_implemented(
        self,
        provider: AbstractFlagProvider,
    ) -> None:
        """Test evaluate_sync raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            provider.evaluate_sync("bool_enabled")

    def test_get_flag_sync_returns_default_when_not_implemented(
        self,
        provider: AbstractFlagProvider,
    ) -> None:
        """Test get_flag_sync returns default when sync not supported."""
        result = provider.get_flag_sync("nonexistent", default=True)
        assert result is True


class TestFeatureFlagsProvider:
    """Tests for FeatureFlagsProvider DI provider."""

    @pytest.fixture
    def config(self) -> FeatureFlagsConfig:
        """Create test config."""
        return FeatureFlagsConfig(
            enabled=True,
            initial_flags={"test_flag": True, "other_flag": False},
            cache_ttl=30,
            default_enabled=True,
        )

    @pytest.fixture
    def provider(self, config: FeatureFlagsConfig) -> FeatureFlagsProvider:
        """Create provider with config."""
        return FeatureFlagsProvider(config=config)

    def test_creation(self, config: FeatureFlagsConfig) -> None:
        """Test provider creation."""
        provider = FeatureFlagsProvider(config=config)
        assert provider.name == "features"
        assert provider.config_key == "features"

    def test_from_config(self, config: FeatureFlagsConfig) -> None:
        """Test from_config classmethod."""
        provider = FeatureFlagsProvider.from_config(config)
        assert provider._config is config

    @pytest.mark.asyncio
    async def test_register_disabled_config(
        self,
        config: FeatureFlagsConfig,
    ) -> None:
        """Test registration with disabled config."""
        config.enabled = False
        provider = FeatureFlagsProvider(config=config)
        container = MagicMock()
        await provider.register(container)
        first_call = container.singleton.call_args_list[0]
        assert first_call[0][0] is FeatureFlagsConfig

    @pytest.mark.asyncio
    async def test_register_singleton_registrations(
        self,
        provider: FeatureFlagsProvider,
    ) -> None:
        """Test singleton registrations."""
        container = MagicMock()
        await provider.register(container)
        assert container.singleton.call_count >= 2

    @pytest.mark.asyncio
    async def test_register_accepts_rich_flag_definitions(self) -> None:
        """YAML-friendly definitions seed the rich manager without adapters."""
        config = FeatureFlagsConfig(
            initial_flags={
                "rollout": {
                    "type": "percentage",
                    "enabled": True,
                    "percentage": 100,
                },
                "experiment": {
                    "type": "variant",
                    "enabled": True,
                    "variants": {"control": 50, "ranked": 50},
                    "default_variant": "control",
                },
            }
        )
        provider = FeatureFlagsProvider(config=config)
        await provider.register(MagicMock())

        manager = provider.get_manager()
        assert manager is not None
        rollout = await manager.evaluate("rollout", FlagContext(user_id="u-1"))
        experiment = await manager.get_variant(
            "experiment", FlagContext(user_id="u-1")
        )
        assert rollout.reason == "percentage_rollout"
        assert experiment in {"control", "ranked"}

    @pytest.mark.asyncio
    async def test_boot_without_event_bus(
        self,
        provider: FeatureFlagsProvider,
    ) -> None:
        """Test boot when event bus is not available."""
        container = MagicMock()
        container.resolve_optional = AsyncMock(return_value=None)
        await provider.register(container)
        await provider.boot(container)
        assert provider.get_manager() is not None

    @pytest.mark.asyncio
    async def test_boot_with_event_bus(
        self,
        provider: FeatureFlagsProvider,
    ) -> None:
        """Test boot with event bus available."""
        await provider.register(MagicMock())
        container = MagicMock()
        event_bus = MagicMock()
        container.resolve_optional = AsyncMock(return_value=event_bus)
        await provider.boot(container)
        manager = provider.get_manager()
        assert manager is not None

    @pytest.mark.asyncio
    async def test_shutdown(self, provider: FeatureFlagsProvider) -> None:
        """Test shutdown does nothing."""
        await provider.shutdown()

    def test_get_simple_provider_before_register(
        self,
        config: FeatureFlagsConfig,
    ) -> None:
        """Test get_simple_provider returns None before registration."""
        provider = FeatureFlagsProvider(config=config)
        assert provider.get_simple_provider() is None

    def test_get_manager_before_register(
        self,
        config: FeatureFlagsConfig,
    ) -> None:
        """Test get_manager returns None before registration."""
        provider = FeatureFlagsProvider(config=config)
        assert provider.get_manager() is None

    def test_get_simple_provider_after_register(
        self,
        provider: FeatureFlagsProvider,
    ) -> None:
        """Test get_simple_provider returns provider after registration."""
        container = MagicMock()
        import asyncio
        asyncio.run(provider.register(container))
        result = provider.get_simple_provider()
        assert result is not None

    def test_get_manager_after_register(
        self,
        provider: FeatureFlagsProvider,
    ) -> None:
        """Test get_manager returns manager after registration."""
        container = MagicMock()
        import asyncio
        asyncio.run(provider.register(container))
        result = provider.get_manager()
        assert result is not None


class TestLocalProviderSyncMethods:
    """Additional tests for LocalProvider synchronous methods."""

    @pytest.fixture
    def provider(self) -> LocalProvider:
        """Create provider with flags."""
        return LocalProvider({
            "test": Flag("test", enabled=True),
            "variant": Flag(
                "variant",
                type=FlagType.VARIANT,
                enabled=True,
                variants={"control": 50, "treatment": 50},
                default_variant="control",
            ),
        })

    def test_get_flag_sync_returns_default(self, provider: LocalProvider) -> None:
        """Test get_flag_sync returns default for missing flag."""
        result = provider.get_flag_sync("missing", default=True)
        assert result is True

    def test_get_flag_sync_evaluates(self, provider: LocalProvider) -> None:
        """Test get_flag_sync evaluates existing flag."""
        result = provider.get_flag_sync("test")
        assert result is True

    def test_get_variant_sync_returns_default(
        self,
        provider: LocalProvider,
    ) -> None:
        """Test get_variant_sync returns default for missing flag."""
        result = provider.get_variant_sync("missing", default="default")
        assert result == "default"

    def test_get_variant_sync_returns_variant(
        self,
        provider: LocalProvider,
    ) -> None:
        """Test get_variant_sync returns variant value."""
        result = provider.get_variant_sync("variant")
        assert result in ("control", "treatment")


class TestFlagManagerHealthCheck:
    """Tests for FlagManager health check integration."""

    @pytest.fixture
    def provider(self) -> LocalProvider:
        """Create provider."""
        return LocalProvider({"test": Flag("test", enabled=True)})

    @pytest.fixture
    def manager(self, provider: LocalProvider) -> FlagManager:
        """Create manager."""
        return FlagManager(provider=provider, cache_ttl=60)

    @pytest.mark.asyncio
    async def test_is_enabled_none_context(
        self,
        manager: FlagManager,
    ) -> None:
        """Test is_enabled with None context."""
        result = await manager.is_enabled("test")
        assert result is True