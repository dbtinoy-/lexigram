"""Tests for AIProvider health check and shutdown logic."""

from __future__ import annotations

import pytest


class TestAIProviderHealthAndShutdown:
    """Tests for AIProvider health check and shutdown logic."""

    @pytest.mark.asyncio
    async def test_shutdown_tolerates_sub_provider_errors(self) -> None:
        from unittest.mock import AsyncMock, MagicMock
        from lexigram.ai.di.provider import AIProvider

        provider = AIProvider()
        mock_sub = MagicMock()
        mock_sub.shutdown = AsyncMock(side_effect=RuntimeError("Shutdown failed"))
        provider._llm_sub = mock_sub

        await provider.shutdown()

        assert provider._llm_sub is None

    @pytest.mark.asyncio
    async def test_health_check_handles_model_dump_result(self) -> None:
        from unittest.mock import AsyncMock, MagicMock
        from lexigram.ai.di.provider import AIProvider
        from lexigram.contracts import HealthStatus, HealthCheckResult

        provider = AIProvider()

        mock_res = MagicMock()
        mock_res.status = HealthStatus.DEGRADED
        mock_res.model_dump.return_value = {"status": "degraded", "message": "fail"}

        mock_sub = MagicMock()
        mock_sub.health_check = AsyncMock(return_value=mock_res)
        provider._llm_sub = mock_sub

        result = await provider.health_check()

        assert result.status == HealthStatus.DEGRADED
        assert result.details["components"]["llm"]["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_handles_vector_sub_provider(self) -> None:
        from unittest.mock import AsyncMock, MagicMock
        from lexigram.ai.di.provider import AIProvider
        from lexigram.contracts import HealthStatus, HealthCheckResult

        provider = AIProvider()

        mock_vec_health = HealthCheckResult(component="vector", status=HealthStatus.HEALTHY)
        mock_sub = MagicMock()
        mock_sub.health_check = AsyncMock(return_value=mock_vec_health)
        provider._vector_sub = mock_sub

        result = await provider.health_check()

        assert "vector" in result.details["components"]
        assert result.details["components"]["vector"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_vector_failure_sets_degraded(self) -> None:
        from unittest.mock import AsyncMock, MagicMock
        from lexigram.ai.di.provider import AIProvider
        from lexigram.contracts import HealthStatus

        provider = AIProvider()

        mock_sub = MagicMock()
        mock_sub.health_check = AsyncMock(side_effect=RuntimeError("Vector down"))
        provider._vector_sub = mock_sub

        result = await provider.health_check()

        assert result.status == HealthStatus.DEGRADED
        assert "Vector down" in result.error
