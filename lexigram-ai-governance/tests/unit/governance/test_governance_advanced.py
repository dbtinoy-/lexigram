"""Advanced unit tests for AIGovernanceManager — soft limits and auditing."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from lexigram.ai.governance.services.manager import AIGovernanceManager
from lexigram.ai.governance.audit import AIAuditEvent, AuditEventType


@pytest.mark.asyncio
class TestAIGovernanceAdvanced:
    @pytest.fixture
    def make_config(self) -> MagicMock:
        cfg = MagicMock()
        cfg.restricted_models = []
        cfg.rpm_limit = None
        cfg.enforce_budget = True
        cfg.monthly_budget = 100.0
        cfg.soft_limit_pct = 0.5  # 50% soft limit
        cfg.max_request_cost = 10.0
        cfg.model_allowlist = {}
        cfg.model_denylist = {}
        return cfg

    @pytest.fixture
    def mock_persistence(self) -> AsyncMock:
        p = AsyncMock()
        p.get_spend.return_value = 0.0
        p.incr_requests.return_value = 1
        return p

    @pytest.fixture
    def mock_audit_store(self) -> AsyncMock:
        return AsyncMock()

    async def test_soft_limit_callback_invoked(self, make_config, mock_persistence) -> None:
        callback_invoked = asyncio.Event()
        
        async def on_soft_limit(user_id, current_spend, budget):
            callback_invoked.set()

        mgr = AIGovernanceManager(
            config=make_config,
            persistence=mock_persistence,
            on_soft_limit=on_soft_limit
        )
        
        # Spend 60 (above 50% soft limit of 100)
        mock_persistence.get_spend.return_value = 40.0
        await mgr.check_budget(20.0, user_id="u1")
        
        # Wait for callback in background task
        await asyncio.wait_for(callback_invoked.wait(), timeout=1.0)
        assert callback_invoked.is_set()

    async def test_audit_emitted_on_denial(self, make_config, mock_persistence, mock_audit_store) -> None:
        mgr = AIGovernanceManager(
            config=make_config,
            persistence=mock_persistence,
            audit_store=mock_audit_store
        )
        
        # Deny via restricted model
        make_config.restricted_models = ["forbidden-model"]
        await mgr.check_request("forbidden-model", "openai")
        
        # Audit record is scheduled in background
        await asyncio.sleep(0.1) 
        assert mock_audit_store.record.called
        event = mock_audit_store.record.call_args[0][0]
        assert event.event_type == AuditEventType.MODEL_DENIED
        assert event.model == "forbidden-model"
        assert event.status == "denied"

    async def test_audit_emitted_on_budget_exceeded(self, make_config, mock_persistence, mock_audit_store) -> None:
        mgr = AIGovernanceManager(
            config=make_config,
            persistence=mock_persistence,
            audit_store=mock_audit_store
        )
        
        make_config.monthly_budget = 10.0
        mock_persistence.get_spend.return_value = 9.0
        
        await mgr.check_budget(2.0, user_id="u1")
        
        await asyncio.sleep(0.1)
        assert mock_audit_store.record.called
        event = mock_audit_store.record.call_args[0][0]
        assert event.event_type == AuditEventType.BUDGET_EXCEEDED
        assert event.status == "denied"

    async def test_check_request_budget_per_request_limit(self, make_config, mock_persistence) -> None:
        mgr = AIGovernanceManager(config=make_config, persistence=mock_persistence)
        
        # Within limit
        result = await mgr.check_request_budget(5.0)
        assert result.is_ok()
        
        # Exceeds per-request cap (10.0)
        result = await mgr.check_request_budget(15.0)
        assert result.is_err()
        assert "exceeds per-request limit" in str(result.unwrap_err())

    async def test_redis_persistence_auto_creation(self) -> None:
        mock_cache = MagicMock()
        mock_config = MagicMock()
        
        # We need to mock the import of RedisGovernancePersistence
        with patch("lexigram.ai.governance.persistence.RedisGovernancePersistence") as mock_redis_p:
            mgr = AIGovernanceManager(config=mock_config, cache=mock_cache)
            assert mgr._persistence == mock_redis_p.return_value
            mock_redis_p.assert_called_with(mock_cache)
