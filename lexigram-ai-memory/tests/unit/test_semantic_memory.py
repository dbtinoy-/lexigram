"""Unit tests for SemanticMemoryStore, FactStore, and EntityExtractor."""

from __future__ import annotations

import pytest

from lexigram.ai.memory.semantic.entity_extractor import EntityExtractor
from lexigram.ai.memory.semantic.fact_store import FactStore
from lexigram.ai.memory.semantic.store import SemanticMemoryStore

from helpers import make_entry


class TestFactStore:
    def test_add_and_query(self) -> None:
        store = FactStore()
        fid = store.add("alice", "is", "developer")
        facts = store.query_by_subject("alice")
        assert len(facts) == 1
        assert facts[0]["id"] == fid
        assert facts[0]["predicate"] == "is"

    def test_query_prefix_match(self) -> None:
        store = FactStore()
        store.add("alice smith", "has", "python skills")
        store.add("bob", "is", "designer")
        matches = store.query_by_subject("alice")
        assert len(matches) == 1

    def test_get_entity_facts_subject_and_object(self) -> None:
        store = FactStore()
        store.add("alice", "works at", "acme corp")
        store.add("bob", "works at", "alice inc")
        facts = store.get_entity_facts("alice")
        assert len(facts) == 2

    def test_update_confidence(self) -> None:
        store = FactStore()
        fid = store.add("alice", "is", "admin", confidence=0.5)
        store.update_confidence(fid, 0.9)
        facts = store.query_by_subject("alice")
        assert facts[0]["confidence"] == pytest.approx(0.9)

    def test_delete(self) -> None:
        store = FactStore()
        fid = store.add("alice", "is", "developer")
        store.delete(fid)
        assert store.query_by_subject("alice") == []

    def test_clear(self) -> None:
        store = FactStore()
        store.add("a", "b", "c")
        store.clear()
        assert len(store) == 0


class TestEntityExtractor:
    @pytest.mark.asyncio
    async def test_heuristic_extract_is_pattern(self) -> None:
        extractor = EntityExtractor()
        entry = make_entry("Alice is a developer. Bob has python skills.")
        triples = await extractor.extract(entry)
        subjects = [t[0] for t in triples]
        assert "alice" in subjects

    @pytest.mark.asyncio
    async def test_custom_fn_used(self) -> None:
        from unittest.mock import AsyncMock

        custom = AsyncMock(return_value=[("foo", "is", "bar")])
        extractor = EntityExtractor(extract_fn=custom)
        entry = make_entry("some content")
        triples = await extractor.extract(entry)
        assert triples == [("foo", "is", "bar")]


class TestSemanticMemoryStore:
    @pytest.mark.asyncio
    async def test_store_and_query_fact(self) -> None:
        store = SemanticMemoryStore()
        fid = await store.store_fact("alice", "is", "developer", confidence=0.9)
        facts = await store.query_facts("alice")
        assert len(facts) == 1

    @pytest.mark.asyncio
    async def test_min_confidence_filter(self) -> None:
        store = SemanticMemoryStore(min_confidence=0.7)
        await store.store_fact("alice", "is", "developer", confidence=0.5)
        facts = await store.query_facts("alice")
        assert facts == []

    @pytest.mark.asyncio
    async def test_update_fact(self) -> None:
        store = SemanticMemoryStore()
        fid = await store.store_fact("alice", "is", "admin", confidence=0.3)
        await store.update_fact(fid, 0.95)
        facts = await store.query_facts("alice")
        assert facts[0]["confidence"] == pytest.approx(0.95)

    @pytest.mark.asyncio
    async def test_max_facts_per_entity_enforced(self) -> None:
        store = SemanticMemoryStore(max_facts_per_entity=2)
        await store.store_fact("alice", "is", "dev1", confidence=0.5)
        await store.store_fact("alice", "is", "dev2", confidence=0.6)
        await store.store_fact("alice", "is", "dev3", confidence=0.9)
        # Only 2 facts should remain (lowest-confidence evicted)
        facts = await store.query_facts("alice")
        assert len(facts) <= 2

    @pytest.mark.asyncio
    async def test_ingest_with_extractor(self) -> None:
        extractor = EntityExtractor()
        store = SemanticMemoryStore(extractor=extractor)
        entry = make_entry("Alice is a developer. Bob has python skills.")
        count = await store.ingest(entry)
        assert count > 0

    @pytest.mark.asyncio
    async def test_ingest_no_extractor_returns_zero(self) -> None:
        store = SemanticMemoryStore()
        count = await store.ingest(make_entry("something"))
        assert count == 0
