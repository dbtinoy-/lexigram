"""Unit tests for lexigram.ai.governance — audit, manager, and persistence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.governance.audit import (
    AIAuditEvent,
    AuditEventType,
    AuditQuery,
    AuditSummary,
    InMemoryAuditStore,
)
from lexigram.ai.governance.persistence import InMemoryGovernancePersistence


# ── AuditEventType ───────────────────────────────────────────────────


class TestAuditEventType:
    def test_values(self) -> None:
        assert AuditEventType.LLM_CALL == "llm_call"
        assert AuditEventType.MODEL_DENIED == "model_denied"
        assert AuditEventType.BUDGET_EXCEEDED == "budget_exceeded"
        assert AuditEventType.RATE_LIMITED == "rate_limited"
        assert AuditEventType.TOOL_CALL == "tool_call"
        assert AuditEventType.AGENT_EXECUTION == "agent_execution"


# ── AIAuditEvent ─────────────────────────────────────────────────────


class TestAIAuditEvent:
    def test_defaults(self) -> None:
        e = AIAuditEvent(event_type=AuditEventType.LLM_CALL)
        assert e.event_type == AuditEventType.LLM_CALL
        assert e.status == "success"
        assert e.model is None
        assert e.tokens is None
        assert e.cost is None
        assert e.event_id  # auto-generated UUID
        assert e.metadata == {}

    def test_with_all_fields(self) -> None:
        e = AIAuditEvent(
            event_type=AuditEventType.LLM_CALL,
            model="gpt-4o",
            provider="openai",
            user_id="user-1",
            tokens=1500,
            cost=0.045,
            latency_ms=320.0,
            metadata={"key": "value"},
        )
        assert e.model == "gpt-4o"
        assert e.provider == "openai"
        assert e.cost == 0.045
        assert e.latency_ms == 320.0


# ── AuditQuery ───────────────────────────────────────────────────────


class TestAuditQuery:
    def test_defaults(self) -> None:
        q = AuditQuery()
        assert q.limit == 1000
        assert q.offset == 0
        assert q.start is None

    def test_with_filters(self) -> None:
        q = AuditQuery(
            user_id="user-1",
            event_types=[AuditEventType.LLM_CALL],
            model="gpt-4o",
            limit=10,
        )
        assert q.user_id == "user-1"
        assert q.limit == 10


# ── InMemoryAuditStore ───────────────────────────────────────────────


class TestInMemoryAuditStore:
    @pytest.fixture
    def store(self) -> InMemoryAuditStore:
        return InMemoryAuditStore()

    @pytest.mark.asyncio
    async def test_record_and_query(self, store: InMemoryAuditStore) -> None:
        event = AIAuditEvent(
            event_type=AuditEventType.LLM_CALL, model="gpt-4o", user_id="u1"
        )
        await store.record(event)
        results = await store.query(AuditQuery())
        assert len(results) == 1
        assert results[0].model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_query_by_user(self, store: InMemoryAuditStore) -> None:
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL, user_id="a"))
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL, user_id="b"))
        results = await store.query(AuditQuery(user_id="a"))
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_query_by_event_type(self, store: InMemoryAuditStore) -> None:
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL))
        await store.record(AIAuditEvent(event_type=AuditEventType.TOOL_CALL))
        results = await store.query(
            AuditQuery(event_types=[AuditEventType.TOOL_CALL])
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_query_pagination(self, store: InMemoryAuditStore) -> None:
        for _ in range(5):
            await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL))
        results = await store.query(AuditQuery(limit=2))
        assert len(results) == 2
        results_offset = await store.query(AuditQuery(limit=2, offset=3))
        assert len(results_offset) == 2

    @pytest.mark.asyncio
    async def test_aggregate(self, store: InMemoryAuditStore) -> None:
        await store.record(
            AIAuditEvent(
                event_type=AuditEventType.LLM_CALL,
                model="gpt-4o",
                user_id="u1",
                tokens=1000,
                cost=0.03,
            )
        )
        await store.record(
            AIAuditEvent(
                event_type=AuditEventType.LLM_CALL,
                model="gpt-4o",
                user_id="u1",
                tokens=500,
                cost=0.015,
                status="denied",
            )
        )
        summary = await store.aggregate(AuditQuery())
        assert summary.total_events == 2
        assert summary.total_tokens == 1500
        assert summary.total_spend == pytest.approx(0.045)
        assert summary.denied_count == 1
        assert summary.by_model["gpt-4o"] == 2
        assert summary.by_user["u1"] == 2

    @pytest.mark.asyncio
    async def test_empty_aggregate(self, store: InMemoryAuditStore) -> None:
        summary = await store.aggregate(AuditQuery())
        assert summary.total_events == 0
        assert summary.total_spend == 0.0


# ── InMemoryGovernancePersistence ────────────────────────────────────


class TestInMemoryGovernancePersistence:
    @pytest.fixture
    def persistence(self) -> InMemoryGovernancePersistence:
        return InMemoryGovernancePersistence()

    @pytest.mark.asyncio
    async def test_incr_requests(
        self, persistence: InMemoryGovernancePersistence
    ) -> None:
        count = await persistence.incr_requests("user-1", window=60.0)
        assert count == 1
        count = await persistence.incr_requests("user-1", window=60.0)
        assert count == 2

    @pytest.mark.asyncio
    async def test_spend_tracking(
        self, persistence: InMemoryGovernancePersistence
    ) -> None:
        total = await persistence.add_spend("key-1", 0.5, ttl=3600)
        assert total == 0.5
        total = await persistence.add_spend("key-1", 0.3, ttl=3600)
        assert total == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_get_spend_unknown_key(
        self, persistence: InMemoryGovernancePersistence
    ) -> None:
        spend = await persistence.get_spend("nonexistent")
        assert spend == 0.0


# ── AIGovernanceManager ──────────────────────────────────────────────


class TestAIGovernanceManager:
    @pytest.fixture
    def make_config(self) -> MagicMock:
        """Create a mock GovernanceConfig."""
        cfg = MagicMock()
        cfg.restricted_models = []
        cfg.rpm_limit = None
        cfg.enforce_budget = True
        cfg.monthly_budget = 100.0
        cfg.soft_limit_pct = None
        cfg.model_allowlist = {}
        cfg.model_denylist = {}
        return cfg

    @pytest.mark.asyncio
    async def test_check_request_allowed(self, make_config: MagicMock) -> None:
        from lexigram.ai.governance.services.manager import AIGovernanceManager

        mgr = AIGovernanceManager(config=make_config)
        assert await mgr.check_request("gpt-4o", "openai") is True

    @pytest.mark.asyncio
    async def test_check_request_restricted_model(self, make_config: MagicMock) -> None:
        from lexigram.ai.governance.services.manager import AIGovernanceManager

        make_config.restricted_models = ["gpt-4o"]
        mgr = AIGovernanceManager(config=make_config)
        assert await mgr.check_request("gpt-4o", "openai") is False

    @pytest.mark.asyncio
    async def test_check_request_rpm_exceeded(self, make_config: MagicMock) -> None:
        from lexigram.ai.governance.services.manager import AIGovernanceManager

        make_config.rpm_limit = 2
        mgr = AIGovernanceManager(config=make_config)
        assert await mgr.check_request("gpt-4o", "openai") is True
        assert await mgr.check_request("gpt-4o", "openai") is True
        assert await mgr.check_request("gpt-4o", "openai") is False

    @pytest.mark.asyncio
    async def test_check_budget_within_limit(self, make_config: MagicMock) -> None:
        from lexigram.ai.governance.services.manager import AIGovernanceManager

        mgr = AIGovernanceManager(config=make_config)
        assert await mgr.check_budget(50.0) is True

    @pytest.mark.asyncio
    async def test_check_budget_exceeded(self, make_config: MagicMock) -> None:
        from lexigram.ai.governance.services.manager import AIGovernanceManager

        make_config.monthly_budget = 10.0
        mgr = AIGovernanceManager(config=make_config)
        assert await mgr.check_budget(15.0) is False

    @pytest.mark.asyncio
    async def test_check_budget_enforcement_disabled(
        self, make_config: MagicMock
    ) -> None:
        from lexigram.ai.governance.services.manager import AIGovernanceManager

        make_config.enforce_budget = False
        mgr = AIGovernanceManager(config=make_config)
        assert await mgr.check_budget(999999.0) is True

    @pytest.mark.asyncio
    async def test_track_cost(self, make_config: MagicMock) -> None:
        from lexigram.ai.governance.services.manager import AIGovernanceManager

        mgr = AIGovernanceManager(config=make_config)
        await mgr.track_cost(0.05, model="gpt-4o")
        # No assertion needed — just verify it doesn't raise

    def test_check_model_access_allowlist(self, make_config: MagicMock) -> None:
        from lexigram.ai.governance.services.manager import AIGovernanceManager

        make_config.model_allowlist = {"user-1": ["gpt-4*"]}
        make_config.model_denylist = {}
        mgr = AIGovernanceManager(config=make_config)
        assert mgr.check_model_access("user-1", "gpt-4o") is True
        assert mgr.check_model_access("user-1", "claude-3") is False

    def test_check_model_access_denylist(self, make_config: MagicMock) -> None:
        from lexigram.ai.governance.services.manager import AIGovernanceManager

        make_config.model_allowlist = {}
        make_config.model_denylist = {"*": ["gpt-4*"]}
        mgr = AIGovernanceManager(config=make_config)
        assert mgr.check_model_access("user-1", "gpt-4o") is False
        assert mgr.check_model_access("user-1", "claude-3") is True

    def test_reload_config(self, make_config: MagicMock) -> None:
        from lexigram.ai.governance.services.manager import AIGovernanceManager

        mgr = AIGovernanceManager(config=make_config)
        new_config = MagicMock()
        new_config.monthly_budget = 200.0
        new_config.rpm_limit = 100
        new_config.soft_limit_pct = 0.8
        new_config.restricted_models = []
        mgr.reload_config(new_config)
        assert mgr._config is new_config
