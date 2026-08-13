"""Tests for InMemoryAuditStore."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from lexigram.audit.store.memory import InMemoryAuditStore
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity, AuditQuery


class TestInMemoryAuditStore:
    """Tests for InMemoryAuditStore."""

    @pytest.mark.asyncio
    async def test_append_and_query(self) -> None:
        store = InMemoryAuditStore()
        entry = AuditEntry(action="user.login", actor_id="user-1", outcome="success")
        await store.append(entry)
        results = await store.query(AuditQuery())
        assert len(results) == 1
        assert results[0].action == "user.login"

    @pytest.mark.asyncio
    async def test_query_filter_by_actor(self) -> None:
        store = InMemoryAuditStore()
        await store.append(AuditEntry(action="a", actor_id="user-1"))
        await store.append(AuditEntry(action="b", actor_id="user-2"))
        results = await store.query(AuditQuery(actor_id="user-1"))
        assert len(results) == 1
        assert results[0].actor_id == "user-1"

    @pytest.mark.asyncio
    async def test_query_filter_by_source(self) -> None:
        store = InMemoryAuditStore()
        await store.append(AuditEntry(action="a", actor_id="u", source="sql"))
        await store.append(AuditEntry(action="b", actor_id="u", source="admin"))
        results = await store.query(AuditQuery(source="sql"))
        assert all(e.source == "sql" for e in results)

    @pytest.mark.asyncio
    async def test_query_filter_by_severity(self) -> None:
        store = InMemoryAuditStore()
        await store.append(AuditEntry(action="a", actor_id="u", severity=AuditEventSeverity.HIGH))
        await store.append(AuditEntry(action="b", actor_id="u", severity=AuditEventSeverity.LOW))
        results = await store.query(AuditQuery(severity=AuditEventSeverity.HIGH))
        assert len(results) == 1
        assert results[0].severity == AuditEventSeverity.HIGH

    @pytest.mark.asyncio
    async def test_query_filter_by_since(self) -> None:
        store = InMemoryAuditStore()
        old_time = datetime.now(UTC) - timedelta(hours=2)
        new_time = datetime.now(UTC)

        old_entry = dataclasses.replace(
            AuditEntry(action="old", actor_id="u"), occurred_at=old_time
        )
        new_entry = dataclasses.replace(
            AuditEntry(action="new", actor_id="u"), occurred_at=new_time
        )
        await store.append(old_entry)
        await store.append(new_entry)

        since = datetime.now(UTC) - timedelta(hours=1)
        results = await store.query(AuditQuery(since=since))
        assert len(results) == 1
        assert results[0].action == "new"

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        store = InMemoryAuditStore()
        for i in range(5):
            await store.append(AuditEntry(action=f"action.{i}", actor_id="u"))
        count = await store.count(AuditQuery())
        assert count == 5

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        store = InMemoryAuditStore()
        await store.append(AuditEntry(action="x", actor_id="u"))
        store.clear()
        results = await store.query(AuditQuery())
        assert results == []

    @pytest.mark.asyncio
    async def test_max_entries_bounded(self) -> None:
        store = InMemoryAuditStore(max_entries=3)
        for i in range(5):
            await store.append(AuditEntry(action=f"a.{i}", actor_id="u"))
        results = await store.query(AuditQuery(limit=10))
        assert len(results) == 3
