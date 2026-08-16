"""Tests for logging/di/provider module."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from lexigram.logging.di.provider import LoggingProvider


class TestLoggingProviderCreation:
    """Tests for creating LoggingProvider."""

    def test_create_provider(self) -> None:
        """Test creating LoggingProvider."""
        provider = LoggingProvider()
        assert provider.name == "logging"

    def test_dependencies_set(self) -> None:
        """Test dependencies are set."""
        provider = LoggingProvider()
        assert provider.dependencies == ("config",)


class TestLoggingProviderRegister:
    """Tests for register method."""

    @pytest.mark.asyncio
    async def test_register_creates_factory(self) -> None:
        """Test register creates LoggerFactoryProtocol."""
        provider = LoggingProvider()
        mock_container = MagicMock()
        
        await provider.register(mock_container)
        
        # Should have called singleton at least 3 times
        assert mock_container.singleton.call_count >= 3

    @pytest.mark.asyncio
    async def test_register_registers_logger_factory(self) -> None:
        """Test register registers LoggerFactoryProtocol."""
        provider = LoggingProvider()
        mock_container = MagicMock()
        
        await provider.register(mock_container)
        
        calls = mock_container.singleton.call_args_list
        # Verify LoggerFactoryProtocol was registered
        factory_registered = any("LoggerFactoryProtocol" in str(call) for call in calls)
        assert factory_registered is True


class TestLoggingProviderBoot:
    """Tests for boot method."""

    @pytest.mark.asyncio
    async def test_boot_applies_config(self) -> None:
        """Test boot applies logging configuration."""
        provider = LoggingProvider()
        mock_container = MagicMock()
        mock_config = MagicMock()
        mock_config.logging = MagicMock()
        mock_container.resolve = AsyncMock(return_value=mock_config)
        
        with patch("lexigram.logging.configurator.apply_config") as mock_apply:
            await provider.boot(mock_container)
            
            mock_apply.assert_called_once_with(mock_config.logging)


class TestLoggingProviderShutdown:
    """Tests for shutdown method."""

    @pytest.mark.asyncio
    async def test_shutdown_does_nothing(self) -> None:
        """Test shutdown requires no work."""
        provider = LoggingProvider()
        
        # Should not raise
        await provider.shutdown()


class TestLoggingProviderExports:
    """Tests for module exports."""

    def test_logging_provider_exported(self) -> None:
        """Test LoggingProvider is exported."""
        from lexigram.logging.di.provider import LoggingProvider
        assert LoggingProvider is not None