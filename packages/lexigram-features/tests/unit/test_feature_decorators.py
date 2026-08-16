"""Tests for feature flag decorators."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.features import (
    FeatureFlagDisabledError,
    Flag,
    FlagManager,
    LocalProvider,
    feature_flag,
    feature_flag_sync,
    require_flag,
    require_flag_sync,
)


class TestFeatureFlagDecorator:
    """Tests for async feature_flag decorator."""

    @pytest.fixture
    def mock_manager(self) -> MagicMock:
        """Create a mock FlagManager."""
        manager = MagicMock(spec=FlagManager)
        manager.is_enabled = AsyncMock(return_value=True)
        return manager

    @pytest.mark.asyncio
    async def test_decorator_calls_function_when_enabled(
        self,
        mock_manager: MagicMock,
    ) -> None:
        """Test decorated function runs when flag is enabled."""
        @feature_flag("test_flag", manager=mock_manager)
        async def my_function() -> str:
            return "executed"

        result = await my_function()
        assert result == "executed"
        mock_manager.is_enabled.assert_called_once_with("test_flag", None)

    @pytest.mark.asyncio
    async def test_decorator_raises_when_disabled(
        self,
        mock_manager: MagicMock,
    ) -> None:
        """Test decorated function raises when flag is disabled."""
        mock_manager.is_enabled = AsyncMock(return_value=False)

        @feature_flag("test_flag", manager=mock_manager)
        async def my_function() -> str:
            return "executed"

        with pytest.raises(FeatureFlagDisabledError) as exc:
            await my_function()
        assert exc.value.flag_name == "test_flag"

    @pytest.mark.asyncio
    async def test_decorator_calls_fallback_when_disabled(
        self,
        mock_manager: MagicMock,
    ) -> None:
        """Test decorated function calls fallback when flag is disabled."""
        mock_manager.is_enabled = AsyncMock(return_value=False)

        @feature_flag("test_flag", manager=mock_manager, fallback=lambda: "fallback")
        async def my_function() -> str:
            return "executed"

        result = await my_function()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_decorator_async_fallback(
        self,
        mock_manager: MagicMock,
    ) -> None:
        """Test decorated function calls async fallback when flag is disabled."""
        mock_manager.is_enabled = AsyncMock(return_value=False)

        async def async_fallback() -> str:
            return "async_fallback"

        @feature_flag("test_flag", manager=mock_manager, fallback=async_fallback)
        async def my_function() -> str:
            return "executed"

        result = await my_function()
        assert result == "async_fallback"

    @pytest.mark.asyncio
    async def test_require_flag_raises_when_disabled(
        self,
        mock_manager: MagicMock,
    ) -> None:
        """Test require_flag raises when flag is disabled."""
        mock_manager.is_enabled = AsyncMock(return_value=False)

        @require_flag("test_flag", manager=mock_manager)
        async def my_function() -> str:
            return "executed"

        with pytest.raises(FeatureFlagDisabledError):
            await my_function()


class TestFeatureFlagSyncDecorator:
    """Tests for sync feature_flag_sync decorator."""

    @pytest.fixture
    def provider(self) -> LocalProvider:
        """Create a provider with test flags."""
        return LocalProvider({
            "enabled_flag": Flag("enabled_flag", enabled=True),
            "disabled_flag": Flag("disabled_flag", enabled=False),
        })

    @pytest.fixture
    def manager(self, provider: LocalProvider) -> FlagManager:
        """Create a manager with the test provider."""
        return FlagManager(provider=provider)

    def test_sync_decorator_calls_function_when_enabled(
        self,
        manager: FlagManager,
    ) -> None:
        """Test sync decorated function runs when flag is enabled."""
        @feature_flag_sync("enabled_flag", manager=manager)
        def my_function() -> str:
            return "executed"

        result = my_function()
        assert result == "executed"

    def test_sync_decorator_raises_when_disabled(
        self,
        manager: FlagManager,
    ) -> None:
        """Test sync decorated function raises when flag is disabled."""
        @feature_flag_sync("disabled_flag", manager=manager)
        def my_function() -> str:
            return "executed"

        with pytest.raises(FeatureFlagDisabledError) as exc:
            my_function()
        assert exc.value.flag_name == "disabled_flag"

    def test_sync_decorator_calls_fallback_when_disabled(
        self,
        manager: FlagManager,
    ) -> None:
        """Test sync decorated function calls fallback when flag is disabled."""
        @feature_flag_sync(
            "disabled_flag",
            manager=manager,
            fallback=lambda: "fallback",
        )
        def my_function() -> str:
            return "executed"

        result = my_function()
        assert result == "fallback"

    def test_require_flag_sync_raises_when_disabled(
        self,
        manager: FlagManager,
    ) -> None:
        """Test require_flag_sync raises when flag is disabled."""
        @require_flag_sync("disabled_flag", manager=manager)
        def my_function() -> str:
            return "executed"

        with pytest.raises(FeatureFlagDisabledError):
            my_function()


class TestFeatureFlagDisabledError:
    """Tests for FeatureFlagDisabledError exception."""

    def test_creation(self) -> None:
        """Test FeatureFlagDisabledError creation."""
        error = FeatureFlagDisabledError("my_feature")

        assert error.flag_name == "my_feature"
        assert "my_feature" in str(error)

    def test_inheritance(self) -> None:
        """Test exception inherits from FeatureFlagError."""
        from lexigram.features import FeatureFlagError

        error = FeatureFlagDisabledError("test_flag")
        assert isinstance(error, FeatureFlagError)
