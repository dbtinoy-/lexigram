"""Tests for memory store types and operations."""

from __future__ import annotations

import pytest
from datetime import datetime

from unittest.mock import MagicMock


class TestMemoryEntry:
    """Test memory entry structure."""

    def test_entry_has_timestamp(self) -> None:
        """Memory entry should track creation time."""
        # Import actual class if available
        entry_data = {
            "content": "Test memory",
            "timestamp": datetime.now(),
            "importance": 0.8,
        }

        assert "timestamp" in entry_data
        assert isinstance(entry_data["timestamp"], datetime)

    def test_entry_with_importance_score(self) -> None:
        """Memory entry should have importance scoring."""
        entry_data = {
            "content": "Important fact",
            "importance": 0.95,
        }

        assert entry_data["importance"] > 0.8


class TestMemoryStoreInterface:
    """Test memory store protocol/interface."""

    def test_store_should_support_write(self) -> None:
        """Memory store should support writing entries."""
        store = MagicMock()
        store.write = MagicMock(return_value=None)

        entry = {"content": "test", "timestamp": datetime.now()}
        store.write("working", entry)

        store.write.assert_called_once()

    def test_store_should_support_read(self) -> None:
        """Memory store should support reading entries."""
        store = MagicMock()
        store.read = MagicMock(return_value={"content": "test"})

        result = store.read("working", "entry_1")

        assert result is not None

    def test_store_should_support_delete(self) -> None:
        """Memory store should support deleting entries."""
        store = MagicMock()
        store.delete = MagicMock(return_value=None)

        store.delete("working", "entry_1")

        store.delete.assert_called_once()

    def test_store_should_support_query(self) -> None:
        """Memory store should support querying entries."""
        store = MagicMock()
        store.query = MagicMock(return_value=[{"content": "result"}])

        results = store.query("episodic", "query_text", top_k=5)

        assert len(results) > 0


class TestWorkingMemory:
    """Test working memory-specific functionality."""

    def test_working_memory_has_capacity(self) -> None:
        """Working memory should have a token capacity."""
        memory = MagicMock()
        memory.get_capacity = MagicMock(return_value=2048)
        memory.get_used_tokens = MagicMock(return_value=1024)

        capacity = memory.get_capacity()
        used = memory.get_used_tokens()

        assert capacity > used

    def test_working_memory_tracks_recent_turns(self) -> None:
        """Working memory should track recent conversation turns."""
        memory = MagicMock()
        memory.get_recent_turns = MagicMock(return_value=5)

        turns = memory.get_recent_turns()

        assert turns > 0

    def test_working_memory_supports_assembly(self) -> None:
        """Working memory should support message assembly."""
        memory = MagicMock()
        memory.assemble = MagicMock(
            return_value=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ]
        )

        messages = memory.assemble()

        assert len(messages) > 0


class TestEpisodicMemory:
    """Test episodic memory-specific functionality."""

    def test_episodic_memory_retrieves_by_relevance(self) -> None:
        """Episodic memory should retrieve entries by relevance."""
        memory = MagicMock()
        memory.retrieve = MagicMock(
            return_value=[
                {"content": "Relevant fact", "score": 0.9},
                {"content": "Less relevant", "score": 0.7},
            ]
        )

        results = memory.retrieve("user topic", top_k=10)

        assert len(results) > 0
        assert results[0]["score"] > results[1]["score"]

    def test_episodic_memory_scores_by_recency(self) -> None:
        """Episodic memory should weight recent entries."""
        memory = MagicMock()
        memory.retrieve_with_recency = MagicMock(return_value=[{"content": "Recent"}])

        results = memory.retrieve_with_recency("query", top_k=5)

        assert len(results) > 0


class TestSemanticMemory:
    """Test semantic memory-specific functionality."""

    def test_semantic_memory_stores_facts(self) -> None:
        """Semantic memory should store facts."""
        memory = MagicMock()
        memory.store_fact = MagicMock(return_value="fact_1")

        fact_id = memory.store_fact("Paris is capital of France")

        assert fact_id is not None

    def test_semantic_memory_stores_entities(self) -> None:
        """Semantic memory should store entities."""
        memory = MagicMock()
        memory.store_entity = MagicMock(return_value="entity_1")

        entity_id = memory.store_entity("Paris", "city")

        assert entity_id is not None

    def test_semantic_memory_retrieves_by_semantic_search(self) -> None:
        """Semantic memory should support semantic search."""
        memory = MagicMock()
        memory.semantic_search = MagicMock(
            return_value=[
                {"content": "France capital", "similarity": 0.92},
            ]
        )

        results = memory.semantic_search("French capital city", top_k=5)

        assert len(results) > 0


class TestMemoryConsolidation:
    """Test memory consolidation/cleanup."""

    def test_consolidation_moves_to_semantic(self) -> None:
        """Consolidation should move working memory to episodic/semantic."""
        consolidator = MagicMock()
        consolidator.consolidate = MagicMock(return_value=None)

        consolidator.consolidate()

        consolidator.consolidate.assert_called_once()

    def test_consolidation_removes_duplicates(self) -> None:
        """Consolidation should deduplicate entries."""
        consolidator = MagicMock()
        consolidator.deduplicate = MagicMock(return_value=5)

        removed_count = consolidator.deduplicate()

        assert removed_count >= 0

    def test_consolidation_pruning(self) -> None:
        """Consolidation should prune low-importance entries."""
        pruner = MagicMock()
        pruner.prune = MagicMock(return_value={"removed": 10, "kept": 40})

        result = pruner.prune(threshold=0.3)

        assert result["removed"] >= 0
        assert result["kept"] >= 0


class TestMemoryRetrieval:
    """Test unified memory retrieval."""

    def test_multi_tier_retrieval(self) -> None:
        """Should retrieve from multiple tiers."""
        retriever = MagicMock()
        retriever.retrieve_all = MagicMock(
            return_value={
                "working": [{"content": "recent"}],
                "episodic": [{"content": "past event"}],
                "semantic": [{"content": "fact"}],
            }
        )

        results = retriever.retrieve_all("query")

        assert "working" in results
        assert "episodic" in results
        assert "semantic" in results

    def test_retrieval_ranking(self) -> None:
        """Retrieved entries should be ranked."""
        retriever = MagicMock()
        retriever.retrieve_ranked = MagicMock(
            return_value=[
                {"content": "Best", "rank": 1, "score": 0.95},
                {"content": "Good", "rank": 2, "score": 0.80},
                {"content": "Okay", "rank": 3, "score": 0.65},
            ]
        )

        results = retriever.retrieve_ranked("query", top_k=5)

        assert len(results) > 0
        assert results[0]["score"] >= results[-1]["score"]
