"""Tests for Result pattern in memory system."""

import pytest
from lexigram.contracts.ai.exceptions import AIMemoryError
from lexigram.ai.memory.services.result_pattern_service import MemorySystemWithResultPattern

class TestMemorySystemResultPattern:
    """Test Result pattern in memory system."""

    @pytest.fixture
    def memory_system(self) -> MemorySystemWithResultPattern:
        """Create memory system."""
        return MemorySystemWithResultPattern()

    @pytest.mark.asyncio
    async def test_store_fact_returns_ok(self, memory_system):
        """Verify store_fact returns Ok."""
        result = await memory_system.store_fact("Python is great", "programming")
        assert result.is_ok()
        fact_id = result.unwrap()
        assert isinstance(fact_id, str)

    @pytest.mark.asyncio
    async def test_store_fact_returns_err_for_empty(self, memory_system):
        """Verify store_fact returns Err for empty fact."""
        result = await memory_system.store_fact("")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), AIMemoryError)

    @pytest.mark.asyncio
    async def test_retrieve_facts_returns_ok(self, memory_system):
        """Verify retrieve_facts returns Ok."""
        result = await memory_system.retrieve_facts("programming")
        assert result.is_ok()
        facts = result.unwrap()
        assert isinstance(facts, list)
