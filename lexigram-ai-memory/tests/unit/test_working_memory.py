"""Unit tests for WorkingMemoryManager and TokenBudgetAllocator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.memory.config import WorkingMemoryConfig
from lexigram.ai.memory.working.manager import WorkingMemoryManager
from lexigram.ai.memory.working.token_budget import TokenBudgetAllocator
from lexigram.contracts.ai.memory import MemorySearchResult

from helpers import make_entry


class TestTokenBudgetAllocator:
    def test_allocate_sums_to_total(self) -> None:
        allocator = TokenBudgetAllocator()
        budget = allocator.allocate(1000)
        assert sum(budget.values()) == 1000

    def test_allocate_respects_fractions(self) -> None:
        config = WorkingMemoryConfig(
            system_prompt_tokens=0,
            recent_turns_fraction=0.5,
            episodic_fraction=0.5,
            semantic_fraction=0.0,
            tool_descriptions_fraction=0.0,
        )
        allocator = TokenBudgetAllocator(config)
        budget = allocator.allocate(100)
        assert budget["recent_turns"] == 50
        assert budget["episodic"] == 50

    def test_budget_for_section(self) -> None:
        allocator = TokenBudgetAllocator()
        val = allocator.budget_for("recent_turns", 1000)
        assert isinstance(val, int)
        assert val > 0

    def test_allocate_custom_total_zero(self) -> None:
        allocator = TokenBudgetAllocator()
        budget = allocator.allocate(0)
        assert all(v == 0 for v in budget.values())


class TestWorkingMemoryManager:
    @pytest.fixture
    def mock_episodic(self) -> MagicMock:
        ep = MagicMock()
        ep.recall = AsyncMock(return_value=[])
        ep.record = AsyncMock()
        return ep

    @pytest.fixture
    def mock_semantic(self) -> MagicMock:
        sem = MagicMock()
        sem.query_facts = AsyncMock(return_value=[])
        return sem

    @pytest.mark.asyncio
    async def test_flush_clears_entries(
        self, mock_episodic: MagicMock, mock_semantic: MagicMock
    ) -> None:
        mgr = WorkingMemoryManager(episodic=mock_episodic, semantic=mock_semantic)
        await mgr.add(make_entry("some thing"))
        assert len(await mgr.get_context_entries()) == 1
        await mgr.flush()
        assert await mgr.get_context_entries() == []

    @pytest.mark.asyncio
    async def test_add_records_to_episodic(self, mock_episodic: MagicMock) -> None:
        mgr = WorkingMemoryManager(episodic=mock_episodic)
        entry = make_entry("hello")
        await mgr.add(entry)
        mock_episodic.record.assert_awaited_once_with(entry)

    @pytest.mark.asyncio
    async def test_assemble_returns_episodic_results(
        self, mock_episodic: MagicMock
    ) -> None:
        entry = make_entry("from episodic")
        mock_episodic.recall = AsyncMock(
            return_value=[MemorySearchResult(entry=entry, score=0.9, source="episodic")]
        )
        mgr = WorkingMemoryManager(episodic=mock_episodic)
        result = await mgr.assemble("query", 2000, owner_id="owner-1")
        assert any(e.id == entry.id for e in result)

    @pytest.mark.asyncio
    async def test_assemble_no_sources(self) -> None:
        mgr = WorkingMemoryManager()
        result = await mgr.assemble("query", 2000, owner_id="owner-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_context_entries_after_assemble(
        self, mock_episodic: MagicMock
    ) -> None:
        entry = make_entry("assembled")
        mock_episodic.recall = AsyncMock(
            return_value=[MemorySearchResult(entry=entry, score=0.8, source="episodic")]
        )
        mgr = WorkingMemoryManager(episodic=mock_episodic)
        await mgr.assemble("something", 1000, owner_id="owner-1")
        ctx = await mgr.get_context_entries()
        assert any(e.id == entry.id for e in ctx)
