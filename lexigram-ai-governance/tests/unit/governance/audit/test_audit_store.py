"""Unit tests for lexigram.ai.governance.audit.store — InMemoryAuditStore."""

from __future__ import annotations

import pytest

from lexigram.ai.governance.audit import (
    AIAuditEvent,
    AuditEventType,
    AuditQuery,
    InMemoryAuditStore,
)


class TestInMemoryAIAuditStore:
    @pytest.fixture
    def store(self) -> InMemoryAuditStore:
        return InMemoryAuditStore()

    @pytest.mark.asyncio
    async def test_record_stores_audit_event(self, store: InMemoryAuditStore) -> None:
        event = AIAuditEvent(
            event_type=AuditEventType.LLM_CALL,
            model="gpt-4o",
            user_id="user-1",
            cost=0.05,
            tokens=1000,
        )
        await store.record(event)
        results = await store.query(AuditQuery())
        assert len(results) == 1
        assert results[0].event_type == AuditEventType.LLM_CALL
        assert results[0].model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_query_by_session_filters(self, store: InMemoryAuditStore) -> None:
        await store.record(
            AIAuditEvent(event_type=AuditEventType.LLM_CALL, user_id="user-1", metadata={"session_id": "sess-1"})
        )
        await store.record(
            AIAuditEvent(event_type=AuditEventType.LLM_CALL, user_id="user-2", metadata={"session_id": "sess-2"})
        )
        results = await store.query(AuditQuery())
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_query_by_user_filters(self, store: InMemoryAuditStore) -> None:
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL, user_id="alice"))
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL, user_id="bob"))
        await store.record(AIAuditEvent(event_type=AuditEventType.TOOL_CALL, user_id="alice"))
        
        results = await store.query(AuditQuery(user_id="alice"))
        assert len(results) == 2
        for event in results:
            assert event.user_id == "alice"

    @pytest.mark.asyncio
    async def test_query_by_action_filters(self, store: InMemoryAuditStore) -> None:
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL))
        await store.record(AIAuditEvent(event_type=AuditEventType.TOOL_CALL))
        await store.record(AIAuditEvent(event_type=AuditEventType.AGENT_EXECUTION))
        
        results = await store.query(AuditQuery(event_types=[AuditEventType.LLM_CALL]))
        assert len(results) == 1
        assert results[0].event_type == AuditEventType.LLM_CALL

    @pytest.mark.asyncio
    async def test_aggregate_returns_counts(self, store: InMemoryAuditStore) -> None:
        await store.record(
            AIAuditEvent(
                event_type=AuditEventType.LLM_CALL,
                model="gpt-4o",
                user_id="user-1",
                tokens=1000,
                cost=0.03,
            )
        )
        await store.record(
            AIAuditEvent(
                event_type=AuditEventType.LLM_CALL,
                model="gpt-4o",
                user_id="user-1",
                tokens=500,
                cost=0.015,
                status="denied",
            )
        )
        await store.record(
            AIAuditEvent(
                event_type=AuditEventType.TOOL_CALL,
                model=None,
                user_id="user-2",
            )
        )
        
        summary = await store.aggregate(AuditQuery())
        
        assert summary.total_events == 3
        assert summary.total_tokens == 1500
        assert summary.total_spend == pytest.approx(0.045)
        assert summary.denied_count == 1
        assert summary.by_model["gpt-4o"] == 2
        assert summary.by_user["user-1"] == 2


class TestAuditStoreEdgeCases:
    @pytest.fixture
    def store(self) -> InMemoryAuditStore:
        return InMemoryAuditStore()

    @pytest.mark.asyncio
    async def test_empty_query_returns_all(self, store: InMemoryAuditStore) -> None:
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL, user_id="a"))
        await store.record(AIAuditEvent(event_type=AuditEventType.TOOL_CALL, user_id="b"))
        
        results = await store.query(AuditQuery())
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_nonexistent_session_returns_empty(self, store: InMemoryAuditStore) -> None:
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL, user_id="user-1"))
        
        results = await store.query(AuditQuery(user_id="nonexistent"))
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_query_with_model_filter(self, store: InMemoryAuditStore) -> None:
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL, model="gpt-4o"))
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL, model="claude-3"))
        
        results = await store.query(AuditQuery(model="gpt-4o"))
        assert len(results) == 1
        assert results[0].model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_query_with_provider_filter(self, store: InMemoryAuditStore) -> None:
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL, provider="openai"))
        await store.record(AIAuditEvent(event_type=AuditEventType.LLM_CALL, provider="anthropic"))
        
        results = await store.query(AuditQuery(provider="openai"))
        assert len(results) == 1
        assert results[0].provider == "openai"

    @pytest.mark.asyncio
    async def test_aggregate_empty_store(self, store: InMemoryAuditStore) -> None:
        summary = await store.aggregate(AuditQuery())
        
        assert summary.total_events == 0
        assert summary.total_spend == 0.0
        assert summary.total_tokens == 0
        assert summary.denied_count == 0
