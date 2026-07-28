"""Tests for AIHealthMonitor additional edge cases."""

import pytest

from lexigram.ai.observability.health.monitor import AIHealthMonitor
from lexigram.contracts import HealthCheckResult, HealthStatus


@pytest.fixture
def monitor():
    """Create fresh AIHealthMonitor instance."""
    return AIHealthMonitor()


class TestAIHealthMonitorEdgeCases:
    """Additional edge case tests."""

    async def test_check_llm_not_found_returns_unknown(self, monitor):
        result = await monitor.check_llm("nonexistent")

        assert result.status == HealthStatus.UNKNOWN
        assert result.component == "llm.nonexistent"
        assert "No health check configured" in result.message

    async def test_check_vector_not_found_returns_unknown(self, monitor):
        result = await monitor.check_vector("nonexistent")

        assert result.status == HealthStatus.UNKNOWN
        assert result.component == "vector.nonexistent"

    async def test_check_cache_not_found_returns_unknown(self, monitor):
        result = await monitor.check_cache("nonexistent")

        assert result.status == HealthStatus.UNKNOWN
        assert result.component == "cache.nonexistent"

    async def test_check_all_empty_returns_empty_dict(self, monitor):
        result = await monitor.check_all()

        assert result == {}

    async def test_is_ready_empty_returns_true(self, monitor):
        result = await monitor.is_ready()

        assert result is True

    async def test_is_live_empty_returns_true(self, monitor):
        result = await monitor.is_live()

        assert result is True

    async def test_is_live_with_one_healthy(self, monitor):
        async def healthy_check():
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="test",
                message="ok",
            )

        monitor.add_llm_check("provider", healthy_check)

        result = await monitor.is_live()

        assert result is True

    async def test_is_live_with_no_healthy_returns_false(self, monitor):
        async def unhealthy_check():
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component="test",
                message="failed",
            )

        monitor.add_llm_check("provider", unhealthy_check)

        result = await monitor.is_live()

        assert result is False


class TestAIHealthMonitorMethods:
    """Test individual check methods."""

    async def test_add_llm_check_stores_function(self, monitor):
        async def check():
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="test",
                message="ok",
            )

        monitor.add_llm_check("test_provider", check)

        assert "test_provider" in monitor._llm_checks

    async def test_add_vector_check_stores_function(self, monitor):
        async def check():
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="test",
                message="ok",
            )

        monitor.add_vector_check("test_provider", check)

        assert "test_provider" in monitor._vector_checks

    async def test_add_cache_check_stores_function(self, monitor):
        async def check():
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="test",
                message="ok",
            )

        monitor.add_cache_check("test_service", check)

        assert "test_service" in monitor._cache_checks

    async def test_add_embedding_check_stores_function(self, monitor):
        async def check():
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="test",
                message="ok",
            )

        monitor.add_embedding_check("test_model", check)

        assert "test_model" in monitor._embedding_checks