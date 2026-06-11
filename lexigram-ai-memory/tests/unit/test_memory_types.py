"""Unit tests for memory types module."""

from __future__ import annotations

import pytest
from datetime import datetime


class TestMemoryTypesImports:
    """Test that types module exports correctly from contracts."""

    def test_imports_memory_entry(self) -> None:
        from lexigram.ai.memory.types import MemoryEntry
        from lexigram.contracts.ai.memory import MemoryEntry as ContractEntry
        assert MemoryEntry is ContractEntry

    def test_imports_memory_query(self) -> None:
        from lexigram.ai.memory.types import MemoryQuery
        from lexigram.contracts.ai.memory import MemoryQuery as ContractQuery
        assert MemoryQuery is ContractQuery

    def test_imports_memory_search_result(self) -> None:
        from lexigram.ai.memory.types import MemorySearchResult
        from lexigram.contracts.ai.memory import MemorySearchResult as ContractResult
        assert MemorySearchResult is ContractResult

    def test_imports_consolidation_result(self) -> None:
        from lexigram.ai.memory.types import ConsolidationResult
        from lexigram.contracts.ai.memory import ConsolidationResult as ContractResult
        assert ConsolidationResult is ContractResult


class TestMemoryEntry:
    """Test MemoryEntry dataclass."""

    @pytest.fixture
    def sample_entry(self) -> MemoryEntry:
        from lexigram.ai.memory.types import MemoryEntry
        return MemoryEntry(
            id="entry-1",
            owner_id="owner-1",
            content="Test content",
            role="user",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            importance=0.8,
            metadata={"key": "value"},
            embedding=[0.1, 0.2, 0.3],
        )

    def test_creation(self, sample_entry: MemoryEntry) -> None:
        assert sample_entry.id == "entry-1"
        assert sample_entry.content == "Test content"
        assert sample_entry.role == "user"
        assert sample_entry.importance == 0.8

    def test_frozen_immutability(self) -> None:
        from lexigram.ai.memory.types import MemoryEntry
        entry = MemoryEntry(
            id="e1",
            owner_id="owner-1",
            content="c",
            role="user",
            timestamp=datetime.now(),
        )
        with pytest.raises(Exception):
            entry.id = "new-id"

    def test_default_importance(self) -> None:
        from lexigram.ai.memory.types import MemoryEntry
        entry = MemoryEntry(
            id="e1",
            owner_id="owner-1",
            content="c",
            role="user",
            timestamp=datetime.now(),
        )
        assert entry.importance == 0.5

    def test_default_metadata(self) -> None:
        from lexigram.ai.memory.types import MemoryEntry
        entry = MemoryEntry(
            id="e1",
            owner_id="owner-1",
            content="c",
            role="user",
            timestamp=datetime.now(),
        )
        assert entry.metadata == {}

    def test_default_embedding(self) -> None:
        from lexigram.ai.memory.types import MemoryEntry
        entry = MemoryEntry(
            id="e1",
            owner_id="owner-1",
            content="c",
            role="user",
            timestamp=datetime.now(),
        )
        assert entry.embedding is None


class TestMemoryQuery:
    """Test MemoryQuery dataclass."""

    @pytest.fixture
    def sample_query(self) -> MemoryQuery:
        from lexigram.ai.memory.types import MemoryQuery
        return MemoryQuery(
            owner_id="owner-1",
            query="test search",
            top_k=5,
            min_relevance=0.3,
            recency_weight=0.2,
            importance_weight=0.3,
            relevance_weight=0.5,
            filters={"session_id": "sess-123"},
            time_range=(datetime(2024, 1, 1), datetime(2024, 12, 31)),
        )

    def test_creation(self, sample_query: MemoryQuery) -> None:
        assert sample_query.query == "test search"
        assert sample_query.top_k == 5
        assert sample_query.min_relevance == 0.3

    def test_frozen_immutability(self) -> None:
        from lexigram.ai.memory.types import MemoryQuery
        q = MemoryQuery(owner_id="owner-1", query="test")
        with pytest.raises(Exception):
            q.query = "new"

    def test_default_values(self) -> None:
        from lexigram.ai.memory.types import MemoryQuery
        q = MemoryQuery(owner_id="owner-1", query="test")
        assert q.top_k == 10
        assert q.min_relevance == 0.0
        assert q.recency_weight == 0.3
        assert q.importance_weight == 0.3
        assert q.relevance_weight == 0.4
        assert q.filters == {}
        assert q.time_range is None


class TestMemorySearchResult:
    """Test MemorySearchResult dataclass."""

    @pytest.fixture
    def sample_entry(self) -> MemoryEntry:
        from lexigram.ai.memory.types import MemoryEntry
        return MemoryEntry(
            id="e1",
            owner_id="owner-1",
            content="test",
            role="user",
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def sample_result(self, sample_entry: MemoryEntry) -> MemorySearchResult:
        from lexigram.ai.memory.types import MemorySearchResult
        return MemorySearchResult(
            entry=sample_entry,
            score=0.95,
            source="episodic",
        )

    def test_creation(self, sample_result: MemorySearchResult) -> None:
        assert sample_result.score == 0.95
        assert sample_result.source == "episodic"

    def test_frozen_immutability(self, sample_entry: MemoryEntry) -> None:
        from lexigram.ai.memory.types import MemorySearchResult
        result = MemorySearchResult(entry=sample_entry, score=0.5, source="test")
        with pytest.raises(Exception):
            result.score = 0.9


class TestConsolidationResult:
    """Test ConsolidationResult dataclass."""

    def test_creation(self) -> None:
        from lexigram.ai.memory.types import ConsolidationResult
        result = ConsolidationResult(
            entries_processed=100,
            entries_consolidated=20,
            entries_pruned=10,
            entities_extracted=5,
            duration_ms=150.5,
        )
        assert result.entries_processed == 100
        assert result.entries_consolidated == 20
        assert result.entries_pruned == 10
        assert result.entities_extracted == 5
        assert result.duration_ms == 150.5

    def test_frozen_immutability(self) -> None:
        from lexigram.ai.memory.types import ConsolidationResult
        result = ConsolidationResult(
            entries_processed=1,
            entries_consolidated=0,
            entries_pruned=0,
            entities_extracted=0,
            duration_ms=0.0,
        )
        with pytest.raises(Exception):
            result.entries_processed = 2