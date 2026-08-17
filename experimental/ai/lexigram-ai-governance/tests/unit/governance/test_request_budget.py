"""Tests for per-request cost budget enforcement."""

from __future__ import annotations

import pytest

from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance.exceptions import GovernanceError
from lexigram.ai.governance.services.manager import AIGovernanceManager


class TestCheckRequestBudget:
    """Tests for AIGovernanceManager.check_request_budget."""

    def _make_manager(self, **config_kwargs: object) -> AIGovernanceManager:
        """Create a manager with the given config overrides."""
        config = GovernanceConfig(**config_kwargs)  # type: ignore[arg-type]
        return AIGovernanceManager(config=config)

    @pytest.mark.asyncio
    async def test_within_per_request_budget_returns_ok(self) -> None:
        """Request under max_request_cost returns Ok(None)."""
        manager = self._make_manager(max_request_cost=1.0)
        result = await manager.check_request_budget(estimated_cost=0.50)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_over_per_request_budget_returns_err(self) -> None:
        """Request over max_request_cost returns Err(GovernanceError)."""
        manager = self._make_manager(max_request_cost=0.10)
        result = await manager.check_request_budget(estimated_cost=0.50)
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, GovernanceError)
        assert "per-request limit" in str(err)

    @pytest.mark.asyncio
    async def test_none_cap_allows_any_cost(self) -> None:
        """When max_request_cost is None, no per-request cap is applied."""
        manager = self._make_manager(max_request_cost=None)
        result = await manager.check_request_budget(estimated_cost=9999.0)
        assert result.is_ok()
