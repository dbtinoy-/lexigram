"""Unit tests for EpisodicMemoryStore and EpisodicCompressor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.memory.backends.in_memory import InMemoryMemoryBackend
from lexigram.ai.memory.episodic.compressor import EpisodicCompressor
from lexigram.ai.memory.episodic.store import EpisodicMemoryStore
from lexigram.ai.memory.exceptions import ConsolidationError

from helpers import make_entry, make_query


class TestEpisodicMemoryStore:
    @pytest.fixture
    def store(self) -> EpisodicMemoryStore:
        return EpisodicMemoryStore(backend=InMemoryMemoryBackend())

    @pytest.mark.asyncio
    async def test_record_and_recall(self, store: EpisodicMemoryStore) -> None:
        entry = make_entry("user asked about weather")
        await store.record(entry)
        results = await store.recall(make_query("weather"))
        assert len(results) == 1
        assert results[0].entry.id == entry.id

    @pytest.mark.asyncio
    async def test_forget_removes_entry(self, store: EpisodicMemoryStore) -> None:
        entry = make_entry("something to forget")
        await store.record(entry)
        await store.forget(entry.id, "owner-1")
        results = await store.recall(make_query())
        assert all(r.entry.id != entry.id for r in results)

    @pytest.mark.asyncio
    async def test_multiple_entries(self, store: EpisodicMemoryStore) -> None:
        for i in range(5):
            await store.record(make_entry(f"turn {i}"))
        results = await store.recall(make_query(top_k=5))
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_recall_delegates_to_backend(self) -> None:
        mock_backend = MagicMock()
        mock_backend.retrieve = AsyncMock(return_value=[])
        store = EpisodicMemoryStore(backend=mock_backend)
        q = make_query()
        await store.recall(q)
        mock_backend.retrieve.assert_awaited_once_with(q)


class TestEpisodicCompressor:
    @pytest.mark.asyncio
    async def test_compress_empty_raises(self) -> None:
        compressor = EpisodicCompressor()
        with pytest.raises(ConsolidationError, match="empty list"):
            await compressor.compress([])

    @pytest.mark.asyncio
    async def test_compress_fallback(self) -> None:
        compressor = EpisodicCompressor()
        entries = [make_entry(f"message {i}") for i in range(3)]
        result = await compressor.compress(entries)
        assert "summary" in result.content
        assert result.role == "system"
        assert len(result.metadata["compressed_ids"]) == 3

    @pytest.mark.asyncio
    async def test_compress_with_custom_fn(self) -> None:
        target_entry = make_entry("custom summary")
        custom_fn = AsyncMock(return_value=target_entry)
        compressor = EpisodicCompressor(summarise_fn=custom_fn)
        entries = [make_entry(f"m {i}") for i in range(2)]
        result = await compressor.compress(entries)
        assert result.id == target_entry.id
        custom_fn.assert_awaited_once()
