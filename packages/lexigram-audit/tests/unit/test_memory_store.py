"""Tests for InMemoryAuditStore."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from lexigram.audit.store.memory import InMemoryAuditStore
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity, AuditQuery


class TestInMemoryAuditStore:
    """Tests for InMemoryAuditStore."""

    @pytest.fixture
    def store(self) -> InMemoryAuditStore:
        return InMemoryAuditStore()

    @pytest.fixture
    def sample_entry(self) -> AuditEntry:
        return AuditEntry(
            action="user.login",
            actor_id="user-1",
            resource_type="User",
            resource_id="user-1",
            outcome="success",
            severity=AuditEventSeverity.MEDIUM,
            source="test",
        )

    @pytest.mark.asyncio
    async def test_append_adds_entry(self, store: InMemoryAuditStore, sample_entry: AuditEntry) -> None:
        await store.append(sample_entry)
        query = AuditQuery(limit=10)
        results = await store.query(query)
        assert len(results) == 1
        assert results[0].action == "user.login"

    @pytest.mark.asyncio
    async def test_query_returns_newest_first(self, store: InMemoryAuditStore) -> None:
        for i in range(5):
            entry = AuditEntry(action=f"action-{i}", actor_id="user", outcome="success")
            await store.append(entry)
        
        results = await store.query(AuditQuery(limit=10))
        assert results[0].action == "action-4"
        assert results[-1].action == "action-0"

    @pytest.mark.asyncio
    async def test_query_filters_by_actor_id(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(action="a", actor_id="user-1", outcome="success"))
        await store.append(AuditEntry(action="b", actor_id="user-2", outcome="success"))
        
        results = await store.query(AuditQuery(actor_id="user-1", limit=10))
        assert len(results) == 1
        assert results[0].actor_id == "user-1"

    @pytest.mark.asyncio
    async def test_query_filters_by_action(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(action="user.login", actor_id="u", outcome="success"))
        await store.append(AuditEntry(action="user.logout", actor_id="u", outcome="success"))
        
        results = await store.query(AuditQuery(action="user.login", limit=10))
        assert len(results) == 1
        assert results[0].action == "user.login"

    @pytest.mark.asyncio
    async def test_query_filters_by_resource_type(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(action="a", actor_id="u", resource_type="User", outcome="success"))
        await store.append(AuditEntry(action="b", actor_id="u", resource_type="Session", outcome="success"))
        
        results = await store.query(AuditQuery(resource_type="User", limit=10))
        assert len(results) == 1
        assert results[0].resource_type == "User"

    @pytest.mark.asyncio
    async def test_query_filters_by_resource_id(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(action="a", actor_id="u", resource_id="r1", outcome="success"))
        await store.append(AuditEntry(action="b", actor_id="u", resource_id="r2", outcome="success"))
        
        results = await store.query(AuditQuery(resource_id="r1", limit=10))
        assert len(results) == 1
        assert results[0].resource_id == "r1"

    @pytest.mark.asyncio
    async def test_query_filters_by_source(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(action="a", actor_id="u", source="web", outcome="success"))
        await store.append(AuditEntry(action="b", actor_id="u", source="api", outcome="success"))
        
        results = await store.query(AuditQuery(source="web", limit=10))
        assert len(results) == 1
        assert results[0].source == "web"

    @pytest.mark.asyncio
    async def test_query_filters_by_severity(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(action="a", actor_id="u", severity=AuditEventSeverity.LOW, outcome="success"))
        await store.append(AuditEntry(action="b", actor_id="u", severity=AuditEventSeverity.HIGH, outcome="success"))
        
        results = await store.query(AuditQuery(severity=AuditEventSeverity.HIGH, limit=10))
        assert len(results) == 1
        assert results[0].severity == AuditEventSeverity.HIGH

    @pytest.mark.asyncio
    async def test_query_filters_by_outcome(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(action="a", actor_id="u", outcome="success"))
        await store.append(AuditEntry(action="b", actor_id="u", outcome="failure"))
        
        results = await store.query(AuditQuery(outcome="failure", limit=10))
        assert len(results) == 1
        assert results[0].outcome == "failure"

    @pytest.mark.asyncio
    async def test_query_filters_by_tenant_id(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(action="a", actor_id="u", tenant_id="tenant-1", outcome="success"))
        await store.append(AuditEntry(action="b", actor_id="u", tenant_id="tenant-2", outcome="success"))
        
        results = await store.query(AuditQuery(tenant_id="tenant-1", limit=10))
        assert len(results) == 1
        assert results[0].tenant_id == "tenant-1"

    @pytest.mark.asyncio
    async def test_query_filters_by_since(self, store: InMemoryAuditStore) -> None:
        now = datetime.now(UTC)
        old_entry = AuditEntry(action="old", actor_id="u", outcome="success", occurred_at=now - timedelta(days=10))
        new_entry = AuditEntry(action="new", actor_id="u", outcome="success", occurred_at=now)
        await store.append(old_entry)
        await store.append(new_entry)
        
        results = await store.query(AuditQuery(since=now - timedelta(days=1), limit=10))
        assert len(results) == 1
        assert results[0].action == "new"

    @pytest.mark.asyncio
    async def test_query_filters_by_until(self, store: InMemoryAuditStore) -> None:
        now = datetime.now(UTC)
        old_entry = AuditEntry(action="old", actor_id="u", outcome="success", occurred_at=now - timedelta(days=10))
        new_entry = AuditEntry(action="new", actor_id="u", outcome="success", occurred_at=now)
        await store.append(old_entry)
        await store.append(new_entry)
        
        results = await store.query(AuditQuery(until=now - timedelta(days=1), limit=10))
        assert len(results) == 1
        assert results[0].action == "old"

    @pytest.mark.asyncio
    async def test_query_with_offset(self, store: InMemoryAuditStore) -> None:
        for i in range(5):
            await store.append(AuditEntry(action=f"action-{i}", actor_id="u", outcome="success"))
        
        results = await store.query(AuditQuery(limit=2, offset=2))
        assert len(results) == 2
        assert results[0].action == "action-2"

    @pytest.mark.asyncio
    async def test_query_with_limit(self, store: InMemoryAuditStore) -> None:
        for i in range(10):
            await store.append(AuditEntry(action=f"action-{i}", actor_id="u", outcome="success"))
        
        results = await store.query(AuditQuery(limit=3))
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_count_returns_total(self, store: InMemoryAuditStore) -> None:
        for i in range(5):
            await store.append(AuditEntry(action=f"action-{i}", actor_id="u", outcome="success"))
        
        count = await store.count(AuditQuery(limit=10))
        assert count == 5

    @pytest.mark.asyncio
    async def test_count_with_filters(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(action="a", actor_id="user-1", outcome="success"))
        await store.append(AuditEntry(action="b", actor_id="user-2", outcome="success"))
        
        count = await store.count(AuditQuery(actor_id="user-1", limit=10))
        assert count == 1

    @pytest.mark.asyncio
    async def test_clear_removes_all_entries(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(action="a", actor_id="u", outcome="success"))
        store.clear()
        
        results = await store.query(AuditQuery(limit=10))
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_store_respects_max_entries(self) -> None:
        store = InMemoryAuditStore(max_entries=3)
        for i in range(5):
            await store.append(AuditEntry(action=f"action-{i}", actor_id="u", outcome="success"))
        
        results = await store.query(AuditQuery(limit=10))
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_delete_expired_removes_only_expired_entries(self, store: InMemoryAuditStore) -> None:
        now = datetime.now(UTC)
        expired = AuditEntry(
            action="old.login",
            actor_id="user-1",
            outcome="success",
            metadata={"__expires_at": (now - timedelta(days=1)).isoformat()},
        )
        retained = AuditEntry(
            action="recent.login",
            actor_id="user-1",
            outcome="success",
            metadata={"__expires_at": (now + timedelta(days=30)).isoformat()},
        )
        await store.append(expired)
        await store.append(retained)

        deleted = await store.delete_expired(now)

        assert deleted == 1
        results = await store.query(AuditQuery(limit=100))
        assert [e.action for e in results] == ["recent.login"]

    @pytest.mark.asyncio
    async def test_delete_expired_keeps_unstamped_entries(self, store: InMemoryAuditStore, sample_entry: AuditEntry) -> None:
        await store.append(sample_entry)

        deleted = await store.delete_expired(datetime.now(UTC))

        assert deleted == 0
        assert len(await store.query(AuditQuery(limit=10))) == 1


class TestInMemoryAuditStoreNewFields:
    """LXF-003: New fields round-trip and correlation_id filter."""

    @pytest.fixture
    def store(self) -> InMemoryAuditStore:
        return InMemoryAuditStore()

    @pytest.mark.asyncio
    async def test_append_entry_with_new_fields(self, store: InMemoryAuditStore) -> None:
        entry = AuditEntry(
            action="llm.completion",
            actor_id="service-1",
            outcome="success",
            correlation_id="corr-abc",
            causation_id="cause-xyz",
            command_payload_hash=b"abcdef1234567890",
            payload_size_bytes=2048,
        )
        await store.append(entry)
        results = await store.query(AuditQuery(limit=10))
        assert len(results) == 1
        assert results[0].correlation_id == "corr-abc"
        assert results[0].causation_id == "cause-xyz"
        assert results[0].command_payload_hash == b"abcdef1234567890"
        assert results[0].payload_size_bytes == 2048

    @pytest.mark.asyncio
    async def test_query_filters_by_correlation_id(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(
            action="a", actor_id="u", outcome="success", correlation_id="corr-1"
        ))
        await store.append(AuditEntry(
            action="b", actor_id="u", outcome="success", correlation_id="corr-2"
        ))

        results = await store.query(AuditQuery(correlation_id="corr-1", limit=10))
        assert len(results) == 1
        assert results[0].correlation_id == "corr-1"

    @pytest.mark.asyncio
    async def test_query_filters_by_correlation_id_none_match(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(action="a", actor_id="u", outcome="success"))
        results = await store.query(AuditQuery(correlation_id="nonexistent", limit=10))
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_count_with_correlation_id(self, store: InMemoryAuditStore) -> None:
        await store.append(AuditEntry(
            action="a", actor_id="u", outcome="success", correlation_id="corr-1"
        ))
        await store.append(AuditEntry(
            action="b", actor_id="u", outcome="success", correlation_id="corr-2"
        ))
        count = await store.count(AuditQuery(correlation_id="corr-1", limit=10))
        assert count == 1


class TestInMemoryAuditStoreEdgeCases:
    """Edge case tests for InMemoryAuditStore."""

    @pytest.mark.asyncio
    async def test_query_with_no_matching_entries(self) -> None:
        store = InMemoryAuditStore()
        await store.append(AuditEntry(action="a", actor_id="user-1", outcome="success"))
        
        results = await store.query(AuditQuery(actor_id="nonexistent", limit=10))
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_query_with_multiple_filters(self) -> None:
        store = InMemoryAuditStore()
        await store.append(AuditEntry(action="login", actor_id="user-1", resource_type="User", outcome="success"))
        await store.append(AuditEntry(action="login", actor_id="user-1", resource_type="Session", outcome="success"))
        
        results = await store.query(
            AuditQuery(action="login", actor_id="user-1", resource_type="User", limit=10)
        )
        assert len(results) == 1
        assert results[0].resource_type == "User"

    @pytest.mark.asyncio
    async def test_empty_store(self) -> None:
        store = InMemoryAuditStore()
        results = await store.query(AuditQuery(limit=10))
        assert len(results) == 0
