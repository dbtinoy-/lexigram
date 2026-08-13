"""Fail-closed behavior for governance persistence failures (audit §50).

Covers the config flag introduced by the fix and (Task 3) the manager-level
decision applied when the persistence backend is unavailable.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from structlog.testing import capture_logs

from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance.persistence import GovernancePersistence
from lexigram.ai.governance.services.manager import AIGovernanceManager


class TestGovernanceConfigPersistenceFailOpen:
    """The fail-open opt-in flag defaults to fail-closed."""

    def test_default_is_fail_closed(self) -> None:
        config = GovernanceConfig()
        assert config.fail_open_on_persistence_error is False

    def test_explicit_opt_in_overrides_default(self) -> None:
        config = GovernanceConfig(fail_open_on_persistence_error=True)
        assert config.fail_open_on_persistence_error is True


class TestManagerPersistenceFailure:
    """AIGovernanceManager applies the configured decision on persistence failure."""

    def _make_manager(
        self,
        persistence: GovernancePersistence,
        **config_kwargs: object,
    ) -> AIGovernanceManager:
        """Build a manager over *persistence* with the given config overrides."""
        config = GovernanceConfig(**config_kwargs)  # type: ignore[arg-type]
        return AIGovernanceManager(config=config, persistence=persistence)

    @pytest.fixture
    def failing_persistence(self) -> AsyncMock:
        persistence = AsyncMock()
        persistence.incr_requests = AsyncMock(side_effect=RuntimeError("redis down"))
        persistence.get_spend = AsyncMock(side_effect=RuntimeError("redis down"))
        persistence.add_spend = AsyncMock(side_effect=RuntimeError("redis down"))
        return persistence

    @pytest.mark.asyncio
    async def test_check_request_denies_when_persistence_fails(
        self, failing_persistence: AsyncMock
    ) -> None:
        manager = self._make_manager(failing_persistence, rpm_limit=5)

        with capture_logs() as logs:
            allowed = await manager.check_request("gpt-4o", "openai", user_id="u1")

        assert allowed is False
        assert any(
            log.get("event") == "governance_persistence_unavailable"
            and log.get("operation") == "rpm_check"
            and log.get("bucket_key") == "u1"
            and log.get("error_type") == "RuntimeError"
            and log.get("decision") == "denied"
            for log in logs
        )

    @pytest.mark.asyncio
    async def test_check_request_allows_when_fail_open_configured(
        self, failing_persistence: AsyncMock
    ) -> None:
        manager = self._make_manager(
            failing_persistence, rpm_limit=5, fail_open_on_persistence_error=True
        )

        with capture_logs() as logs:
            allowed = await manager.check_request("gpt-4o", "openai", user_id="u1")

        assert allowed is True
        assert any(
            log.get("event") == "governance_persistence_unavailable"
            and log.get("decision") == "allowed"
            for log in logs
        )

    @pytest.mark.asyncio
    async def test_check_budget_denies_when_persistence_fails(
        self, failing_persistence: AsyncMock
    ) -> None:
        manager = self._make_manager(failing_persistence, monthly_budget=100.0)

        with capture_logs() as logs:
            allowed = await manager.check_budget(cost=1.0, user_id="u1")

        assert allowed is False
        assert any(
            log.get("event") == "governance_persistence_unavailable"
            and log.get("operation") == "budget_check"
            and str(log.get("bucket_key") or "").startswith("u1:")
            for log in logs
        )

    @pytest.mark.asyncio
    async def test_check_budget_allows_when_fail_open_configured(
        self, failing_persistence: AsyncMock
    ) -> None:
        manager = self._make_manager(
            failing_persistence,
            monthly_budget=100.0,
            fail_open_on_persistence_error=True,
        )

        with capture_logs() as logs:
            allowed = await manager.check_budget(cost=1.0, user_id="u1")

        assert allowed is True
        assert any(
            log.get("event") == "governance_persistence_unavailable"
            and log.get("decision") == "allowed"
            for log in logs
        )

    @pytest.mark.asyncio
    async def test_check_request_budget_returns_err_on_persistence_failure(
        self, failing_persistence: AsyncMock
    ) -> None:
        manager = self._make_manager(failing_persistence, monthly_budget=100.0)

        result = await manager.check_request_budget(estimated_cost=1.0)

        assert result.is_err()
        assert "would exceed monthly budget" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_track_cost_skips_and_logs_on_persistence_failure(
        self, failing_persistence: AsyncMock
    ) -> None:
        manager = self._make_manager(failing_persistence)

        with capture_logs() as logs:
            await manager.track_cost(cost=0.05, model="gpt-4o", user_id="u1")

        assert any(
            log.get("event") == "governance_persistence_unavailable"
            and log.get("operation") == "cost_track"
            for log in logs
        )
        assert failing_persistence.add_spend.await_count == 1

    @pytest.mark.asyncio
    async def test_redis_persistence_failure_denies_request_end_to_end(self) -> None:
        """Protocol-compliant cache Err → denied + logged through the manager."""
        from lexigram.ai.governance.persistence import RedisGovernancePersistence
        from lexigram.contracts.infra.cache.exceptions import CacheWriteError
        from lexigram.result import Err

        cache = AsyncMock()
        cache._client = None
        cache.client = None
        cache.get.return_value = Err(
            CacheWriteError("ai:gov:req:u1:count", "connection refused")
        )
        cache.set.return_value = Err(
            CacheWriteError("ai:gov:req:u1:count", "connection refused")
        )
        persistence = RedisGovernancePersistence(cache=cache)
        manager = self._make_manager(persistence, rpm_limit=5)

        with capture_logs() as logs:
            allowed = await manager.check_request("gpt-4o", "openai", user_id="u1")

        assert allowed is False
        assert any(
            log.get("event") == "governance_persistence_unavailable"
            and log.get("error_type") == "GovernancePersistenceError"
            and log.get("decision") == "denied"
            for log in logs
        )
