"""Unit tests for InMemoryMemoryBackend."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lexigram.ai.memory.backends.in_memory import InMemoryMemoryBackend
from lexigram.contracts.ai.memory import MemoryEntry, MemoryQuery

from helpers import make_entry, make_query


class TestInMemoryMemoryBackend:
    @pytest.mark.asyncio
    async def test_store_and_get_recent(self, backend: InMemoryMemoryBackend) -> None:
        entry = make_entry("hello world")
        await backend.store(entry)
        recent = await backend.get_recent(10)
        assert len(recent) == 1
        assert recent[0].id == entry.id

    @pytest.mark.asyncio
    async def test_retrieve_returns_scored_results(self, backend: InMemoryMemoryBackend) -> None:
        entry = make_entry("some content", importance=0.9)
        await backend.store(entry)
        results = await backend.retrieve(make_query())
        assert len(results) == 1
        assert results[0].entry.id == entry.id
        assert results[0].source == "in_memory"

    @pytest.mark.asyncio
    async def test_retrieve_respects_top_k(self, backend: InMemoryMemoryBackend) -> None:
        for i in range(5):
            await backend.store(make_entry(f"content {i}"))
        results = await backend.retrieve(make_query(top_k=2))
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_delete_removes_entry(self, backend: InMemoryMemoryBackend) -> None:
        entry = make_entry()
        await backend.store(entry)
        await backend.delete(entry.id)
        recent = await backend.get_recent(10)
        assert all(e.id != entry.id for e in recent)

    @pytest.mark.asyncio
    async def test_clear_removes_all(self, backend: InMemoryMemoryBackend) -> None:
        for i in range(3):
            await backend.store(make_entry(f"entry {i}"))
        await backend.clear()
        recent = await backend.get_recent(10)
        assert recent == []

    @pytest.mark.asyncio
    async def test_retrieve_time_range_filter(self, backend: InMemoryMemoryBackend) -> None:
        now = datetime.now(UTC)
        old = make_entry("old")
        # Manually set an old timestamp via model_copy
        old_ts = MemoryEntry(
            id=old.id,
            content=old.content,
            role=old.role,
            timestamp=now - timedelta(days=5),
            importance=old.importance,
            metadata=old.metadata,
        )
        await backend.store(old_ts)
        new_entry = make_entry("new")
        await backend.store(new_entry)

        # Only retrieve entries from the last 2 days
        query = MemoryQuery(
            query="x",
            time_range=(now - timedelta(days=2), now + timedelta(seconds=1)),
        )
        results = await backend.retrieve(query)
        ids = {r.entry.id for r in results}
        assert new_entry.id in ids
        assert old_ts.id not in ids

    @pytest.mark.asyncio
    async def test_retrieve_metadata_filter(self, backend: InMemoryMemoryBackend) -> None:
        tagged = make_entry("tagged", metadata={"type": "turn"})
        untagged = make_entry("untagged")
        await backend.store(tagged)
        await backend.store(untagged)

        query = MemoryQuery(query="x", filters={"type": "turn"})
        results = await backend.retrieve(query)
        assert all(r.entry.metadata.get("type") == "turn" for r in results)

    @pytest.mark.asyncio
    async def test_get_recent_order(self, backend: InMemoryMemoryBackend) -> None:
        e1 = make_entry("first")
        e2 = make_entry("second")
        e3 = make_entry("third")
        for e in [e1, e2, e3]:
            await backend.store(e)
        recent = await backend.get_recent(3)
        # Newest should come first
        assert recent[0].id == e3.id
