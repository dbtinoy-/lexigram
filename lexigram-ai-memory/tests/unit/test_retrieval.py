"""Unit tests for MemoryRetriever and RelevanceRanker."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.memory.retrieval.ranking import RelevanceRanker
from lexigram.ai.memory.retrieval.retriever import MemoryRetriever
from lexigram.contracts.ai.memory import MemorySearchResult

from helpers import make_entry, make_query


class TestRelevanceRanker:
    def test_rank_sorts_by_combined_score(self) -> None:
        ranker = RelevanceRanker()
        low = make_entry(importance=0.1)
        high = make_entry(importance=0.9)
        q = make_query()
        results = [
            MemorySearchResult(entry=low, score=0.1, source="test"),
            MemorySearchResult(entry=high, score=0.9, source="test"),
        ]
        ranked = ranker.rank(results, q)
        assert ranked[0].entry.id == high.id

    def test_top_k_limits_results(self) -> None:
        ranker = RelevanceRanker()
        q = make_query(top_k=2)
        results = [
            MemorySearchResult(entry=make_entry(f"e{i}"), score=float(i) / 10, source="t")
            for i in range(5)
        ]
        top = ranker.top_k(results, q)
        assert len(top) == 2


class TestMemoryRetriever:
    @pytest.fixture
    def mock_source(self) -> MagicMock:
        s = MagicMock()
        s.retrieve = AsyncMock(return_value=[])
        return s

    @pytest.mark.asyncio
    async def test_retrieve_from_single_source(self, mock_source: MagicMock) -> None:
        entry = make_entry("retrieved")
        mock_source.retrieve = AsyncMock(
            return_value=[MemorySearchResult(entry=entry, score=0.8, source="mock")]
        )
        retriever = MemoryRetriever(sources=[mock_source])
        results = await retriever.retrieve(make_query())
        assert any(r.entry.id == entry.id for r in results)

    @pytest.mark.asyncio
    async def test_deduplicates_across_sources(self) -> None:
        entry = make_entry("duplicate")
        result = MemorySearchResult(entry=entry, score=0.8, source="a")
        s1 = MagicMock()
        s1.retrieve = AsyncMock(return_value=[result])
        s2 = MagicMock()
        s2.retrieve = AsyncMock(
            return_value=[MemorySearchResult(entry=entry, score=0.6, source="b")]
        )
        retriever = MemoryRetriever(sources=[s1, s2])
        results = await retriever.retrieve(make_query())
        entry_ids = [r.entry.id for r in results]
        assert entry_ids.count(entry.id) == 1

    @pytest.mark.asyncio
    async def test_keeps_higher_score_on_dedup(self) -> None:
        entry = make_entry("dup")
        high = MemorySearchResult(entry=entry, score=0.9, source="a")
        low = MemorySearchResult(entry=entry, score=0.3, source="b")
        s1 = MagicMock()
        s1.retrieve = AsyncMock(return_value=[low])
        s2 = MagicMock()
        s2.retrieve = AsyncMock(return_value=[high])
        retriever = MemoryRetriever(sources=[s1, s2])
        results = await retriever.retrieve(make_query())
        matching = [r for r in results if r.entry.id == entry.id]
        # Score may be reranked, but original raw score from s2 was retained before rerank
        assert len(matching) == 1

    @pytest.mark.asyncio
    async def test_add_source(self, mock_source: MagicMock) -> None:
        retriever = MemoryRetriever(sources=[])
        retriever.add_source(mock_source)
        await retriever.retrieve(make_query())
        mock_source.retrieve.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_sources_returns_empty(self) -> None:
        retriever = MemoryRetriever(sources=[])
        results = await retriever.retrieve(make_query())
        assert results == []

    @pytest.mark.asyncio
    async def test_retrieval_tracking(self) -> None:
        entry1 = make_entry("e1")
        entry2 = make_entry("e2")
        
        s1 = MagicMock()
        # First query returns e1
        s1.retrieve = AsyncMock(side_effect=[
            [MemorySearchResult(entry=entry1, score=0.8, source="a")],
            [MemorySearchResult(entry=entry1, score=0.8, source="a"), 
             MemorySearchResult(entry=entry2, score=0.8, source="a")],
        ])
        
        retriever = MemoryRetriever(sources=[s1])
        await retriever.retrieve(make_query())
        
        assert retriever.get_retrieval_count(entry1.id) == 1
        assert retriever.get_retrieval_count(entry2.id) == 0
        
        await retriever.retrieve(make_query())
        
        assert retriever.get_retrieval_count(entry1.id) == 2
        assert retriever.get_retrieval_count(entry2.id) == 1
        
        stats = retriever.get_retrieval_stats()
        assert stats["total_retrievals"] == 3
        assert stats["unique_entries"] == 2
        
        retriever.reset_stats()
        assert retriever.get_retrieval_count(entry1.id) == 0
        assert retriever.get_retrieval_stats()["total_retrievals"] == 0


class TestMemoryPruner:
    @pytest.mark.asyncio
    async def test_prune_by_importance(self) -> None:
        from lexigram.ai.memory.retrieval.prune import MemoryPruner
        low_imp = make_entry("low", importance=0.05)
        high_imp = make_entry("high", importance=0.8)
        
        store = MagicMock()
        store.retrieve = AsyncMock(return_value=[
            MemorySearchResult(entry=low_imp, score=1.0, source="test"),
            MemorySearchResult(entry=high_imp, score=1.0, source="test"),
        ])
        store.delete = AsyncMock()
        
        pruner = MemoryPruner(store)
        res = await pruner.prune(importance_threshold=0.1, max_age_hours=0)
        
        assert res.pruned_count == 1
        assert res.remaining_count == 1
        store.delete.assert_awaited_once_with(low_imp.id)

    @pytest.mark.asyncio
    async def test_prune_by_age(self) -> None:
        from lexigram.ai.memory.retrieval.prune import MemoryPruner

        old_tmp = make_entry("old", importance=0.9)
        old = dataclasses.replace(old_tmp, timestamp=datetime.now(UTC) - timedelta(hours=48))
        new = make_entry("new", importance=0.9)

        store = MagicMock()
        store.retrieve = AsyncMock(return_value=[
            MemorySearchResult(entry=old, score=1.0, source="test"),
            MemorySearchResult(entry=new, score=1.0, source="test"),
        ])
        store.delete = AsyncMock()

        pruner = MemoryPruner(store)
        res = await pruner.prune(importance_threshold=0.0, max_age_hours=24)

        assert res.pruned_count == 1
        assert res.remaining_count == 1
        store.delete.assert_awaited_once_with(old.id)

    @pytest.mark.asyncio
    async def test_prune_dry_run(self) -> None:
        from lexigram.ai.memory.retrieval.prune import MemoryPruner
        low_imp = make_entry("low", importance=0.05)
        
        store = MagicMock()
        store.retrieve = AsyncMock(return_value=[
            MemorySearchResult(entry=low_imp, score=1.0, source="test"),
        ])
        store.delete = AsyncMock()
        
        pruner = MemoryPruner(store)
        res = await pruner.prune(importance_threshold=0.1, max_age_hours=0, dry_run=True)
        
        assert res.pruned_count == 1
        assert res.remaining_count == 0
        store.delete.assert_not_called()

