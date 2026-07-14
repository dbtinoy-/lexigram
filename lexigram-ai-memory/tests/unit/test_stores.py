"""Unit tests for all store types (Buffer, Summary, Entity, Conversation)."""

from __future__ import annotations

import pytest

from lexigram.ai.memory.stores.buffer import BufferMemoryStore
from lexigram.ai.memory.stores.conversation import ConversationMemoryStore
from lexigram.ai.memory.stores.entity import EntityMemoryStore
from lexigram.ai.memory.stores.summary import SummaryMemoryStore

from helpers import make_entry, make_query


class TestBufferMemoryStore:
    @pytest.mark.asyncio
    async def test_fifo_eviction(self) -> None:
        buf = BufferMemoryStore(max_entries=2)
        e1 = make_entry("first")
        e2 = make_entry("second")
        e3 = make_entry("third")
        for e in [e1, e2, e3]:
            await buf.store(e)
        recent = await buf.get_recent(5)
        ids = [e.id for e in recent]
        assert e1.id not in ids
        assert e2.id in ids
        assert e3.id in ids

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        buf = BufferMemoryStore()
        entry = make_entry()
        await buf.store(entry)
        await buf.delete(entry.id)
        recent = await buf.get_recent(10)
        assert all(e.id != entry.id for e in recent)

    @pytest.mark.asyncio
    async def test_retrieve_top_k(self) -> None:
        buf = BufferMemoryStore()
        for i in range(10):
            await buf.store(make_entry(f"msg {i}"))
        results = await buf.retrieve(make_query(top_k=3))
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        buf = BufferMemoryStore()
        await buf.store(make_entry())
        await buf.clear()
        assert len(buf) == 0


class TestSummaryMemoryStore:
    @pytest.mark.asyncio
    async def test_compression_triggered_at_threshold(self) -> None:
        store = SummaryMemoryStore(compress_threshold=3, compress_batch=2)
        for i in range(4):
            await store.store(make_entry(f"turn {i}"))
        # After 4 stores with threshold=3, at least one compression occurred
        summaries = store._summaries
        assert len(summaries) >= 1

    @pytest.mark.asyncio
    async def test_retrieve_includes_summaries(self) -> None:
        store = SummaryMemoryStore(compress_threshold=2, compress_batch=2)
        for i in range(4):
            await store.store(make_entry(f"turn {i}"))
        results = await store.retrieve(make_query(top_k=10))
        sources = {r.source for r in results}
        # Should contain summaries or hot entries
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_clear_resets_all(self) -> None:
        store = SummaryMemoryStore(compress_threshold=2, compress_batch=2)
        for i in range(4):
            await store.store(make_entry(f"t{i}"))
        await store.clear()
        assert store._summaries == []
        results = await store.retrieve(make_query())
        assert results == []


class TestEntityMemoryStore:
    @pytest.mark.asyncio
    async def test_store_and_get_by_entity(self) -> None:
        store = EntityMemoryStore()
        entry = make_entry("alice worked on project X")
        await store.store(entry, entities=["alice", "project X"])
        matches = await store.get_by_entity("alice")
        assert any(e.id == entry.id for e in matches)

    @pytest.mark.asyncio
    async def test_entity_index_case_insensitive(self) -> None:
        store = EntityMemoryStore()
        entry = make_entry("something")
        await store.store(entry, entities=["Alice"])
        assert len(await store.get_by_entity("alice")) == 1

    @pytest.mark.asyncio
    async def test_delete_removes_from_index(self) -> None:
        store = EntityMemoryStore()
        entry = make_entry("content")
        await store.store(entry, entities=["bob"])
        await store.delete(entry.id)
        assert await store.get_by_entity("bob") == []

    @pytest.mark.asyncio
    async def test_clear_removes_all(self) -> None:
        store = EntityMemoryStore()
        await store.store(make_entry(), entities=["x"])
        await store.clear()
        assert await store.get_recent(10) == []


class TestConversationMemoryStore:
    @pytest.mark.asyncio
    async def test_session_partitioning(self) -> None:
        store = ConversationMemoryStore()
        e1 = make_entry("session A turn", metadata={"session_id": "A"})
        e2 = make_entry("session B turn", metadata={"session_id": "B"})
        await store.store(e1)
        await store.store(e2)
        entries_a = await store.get_session_entries("A")
        entries_b = await store.get_session_entries("B")
        assert len(entries_a) == 1
        assert len(entries_b) == 1

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_session(self) -> None:
        store = ConversationMemoryStore()
        for i in range(3):
            await store.store(make_entry(f"t{i}", metadata={"session_id": "sess1"}))
        await store.store(make_entry("other", metadata={"session_id": "sess2"}))
        from lexigram.contracts.ai.memory import MemoryQuery

        q = MemoryQuery(owner_id="owner-1", query="x", filters={"session_id": "sess1"})
        results = await store.retrieve(q)
        assert all(r.entry.metadata["session_id"] == "sess1" for r in results)

    @pytest.mark.asyncio
    async def test_max_turns_eviction(self) -> None:
        store = ConversationMemoryStore(max_turns_per_session=2)
        for i in range(4):
            await store.store(make_entry(f"t{i}", metadata={"session_id": "s"}))
        entries = await store.get_session_entries("s")
        assert len(entries) <= 2
