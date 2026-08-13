"""Edge case tests to improve coverage for Lexigram AI."""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.ai.config import AIConfig, _DisabledSubsystem
from lexigram.ai.di.provider import AIProvider
from lexigram.contracts.core import HealthStatus, HealthCheckResult


class TestConfigEdgeCases:
    """Tests for config.py edge cases."""

    def test_disabled_subsystem_behavior(self) -> None:
        """_DisabledSubsystem is falsy and returns None for any attribute."""
        sub = _DisabledSubsystem()
        assert not sub
        assert sub.any_attr is None
        assert sub.enabled is False

    def test_aiconfig_with_disabled_subsystems(self) -> None:
        """AIConfig uses _DisabledSubsystem when sub-configs are missing."""
        with patch("lexigram.ai.config.GovernanceConfig", None):
            with patch("lexigram.ai.config.ObservabilityConfig", None):
                config = AIConfig()
                # These lines 110 and 118 in config.py use _DisabledSubsystem()
                # but Pydantic might have already validated them.
                # Actually, they are in Field(default_factory=...)
                assert isinstance(config.governance, _DisabledSubsystem)
                assert isinstance(config.observability, _DisabledSubsystem)


class TestProviderEdgeCases:
    """Tests for provider.py edge cases."""

    @pytest.mark.asyncio
    async def test_boot_resolution_failures(self) -> None:
        """boot() handles optional dependency resolution failures gracefully."""
        from lexigram.contracts import CacheBackendProtocol
        from lexigram.contracts.data import DatabaseProviderProtocol

        provider = AIProvider()
        mock_container = AsyncMock()

        # All resolutions fail — boot() should not raise
        mock_container.resolve.side_effect = ValueError("Not found")
        await provider.boot(mock_container)

        mock_container.resolve.assert_any_call(DatabaseProviderProtocol)
        assert provider._database_provider is None
        assert provider._cache_backend is None

    @pytest.mark.asyncio
    async def test_boot_cache_backend_resolution_failure(self) -> None:
        """boot() leaves _cache_backend None when CacheBackendProtocol is unavailable."""
        from lexigram.contracts import CacheBackendProtocol
        from lexigram.contracts.data import DatabaseProviderProtocol

        provider = AIProvider()
        mock_container = AsyncMock()

        async def mock_resolve(contract):
            if contract == CacheBackendProtocol:
                raise KeyError("No cache")
            return None

        mock_container.resolve.side_effect = mock_resolve
        await provider.boot(mock_container)

        mock_container.resolve.assert_any_call(CacheBackendProtocol)
        assert provider._cache_backend is None
        assert provider._rag_cache is None

    @pytest.mark.asyncio
    async def test_boot_creates_rag_cache_when_cache_backend_available(self) -> None:
        """boot() creates RAGCache when CacheBackendProtocol resolves successfully."""
        from lexigram.contracts import CacheBackendProtocol

        provider = AIProvider()
        mock_container = AsyncMock()
        mock_cache = MagicMock()

        async def mock_resolve(contract):
            if contract == CacheBackendProtocol:
                return mock_cache
            return None

        mock_container.resolve.side_effect = mock_resolve
        await provider.boot(mock_container)

        assert provider._cache_backend is mock_cache
        assert provider._rag_cache is not None

    @pytest.mark.asyncio
    async def test_health_check_various_responses(self) -> None:
        """health_check() handles various sub-provider response formats."""
        provider = AIProvider()
        
        # Case 1: Sub-provider returns a dict
        mock_llm = MagicMock()
        mock_llm.health_check = AsyncMock(return_value={"status": "degraded", "reason": "high latency"})
        provider._llm_sub = mock_llm
        
        result = await provider.health_check()
        assert result.status == HealthStatus.DEGRADED
        assert result.details["components"]["llm"]["status"] == "degraded"
        
        # Case 2: Sub-provider returns something else (neither dict nor model_dump)
        mock_llm.health_check = AsyncMock(return_value="OK")
        result = await provider.health_check()
        assert result.details["components"]["llm"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_vector_health_check_responses(self) -> None:
        """health_check() handles vector sub-provider response formats."""
        provider = AIProvider()
        
        mock_vec = MagicMock()
        # Case 1: HealthCheckResult with DEGRADED status
        v_health = HealthCheckResult(component="vector", status=HealthStatus.DEGRADED)
        mock_vec.health_check = AsyncMock(return_value=v_health)
        provider._vector_sub = mock_vec
        
        result = await provider.health_check()
        assert result.status == HealthStatus.DEGRADED
        
        # Case 2: Vector returns a dict
        mock_vec.health_check = AsyncMock(return_value={"status": "healthy"})
        result = await provider.health_check()
        assert result.details["components"]["vector"]["status"] == "healthy"
        
        # Case 3: Vector returns something else
        mock_vec.health_check = AsyncMock(return_value="WEIRD")
        result = await provider.health_check()
        assert result.details["components"]["vector"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_shutdown_exceptions(self) -> None:
        """shutdown() captures but logs sub-provider shutdown errors."""
        provider = AIProvider()
        mock_sub = MagicMock()
        mock_sub.shutdown = AsyncMock(side_effect=RuntimeError("Shutdown failed"))
        provider._llm_sub = mock_sub
        
        # Should not raise
        await provider.shutdown()
        assert provider._llm_sub is None


class TestConstantsEdgeCases:
    """Tests for constants.py edge cases."""

    def test_constants_values(self) -> None:
        """Verify constants are defined."""
        from lexigram.ai import constants
        assert constants.ENV_PREFIX == "LEX_AI__"
        assert constants.ENV_NESTED_DELIMITER == "__"

    def test_constants_version_import_error(self) -> None:
        """Verify version fallback when importlib.metadata fails."""
        import importlib
        from lexigram.ai import constants
        
        with patch("importlib.metadata.version", side_effect=ImportError):
            # Reload to trigger the try/except block
            importlib.reload(constants)
            assert constants.__version__ == "0.0.0"
        
        # Reload again to restore the real version for other tests
        importlib.reload(constants)


class TestTypesEdgeCases:
    """Tests for types.py edge cases."""

    def test_aibaseevent_serialization(self) -> None:
        """Manually test the model_serializer in AIBaseEvent."""
        from lexigram.ai.types import AIBaseEvent
        from datetime import datetime, UTC
        
        event = AIBaseEvent()
        event.timestamp = datetime(2024, 1, 1, tzinfo=UTC)
        
        # Manually call the serializer as Pydantic would
        # handler is a mock that returns the dict
        handler = lambda x: {"timestamp": x.timestamp, "metadata": x.metadata}
        
        data = event.serialize_model(handler)
        assert data["timestamp"] == "2024-01-01T00:00:00+00:00"
        
        # Test with non-datetime
        handler_no_dt = lambda x: {"timestamp": "already_str"}
        data_str = event.serialize_model(handler_no_dt)
        assert data_str["timestamp"] == "already_str"


class TestProviderImportEdgeCases:
    """Tests for provider.py import edge cases."""

    @pytest.mark.asyncio
    async def test_register_importlib_error(self) -> None:
        """Verify register() handles importlib.metadata unavailability."""
        with patch("importlib.metadata.entry_points", side_effect=ImportError):
            provider = AIProvider()
            mock_container = MagicMock()  # Use MagicMock for sync singleton
            # Should not raise
            await provider.register(mock_container)
