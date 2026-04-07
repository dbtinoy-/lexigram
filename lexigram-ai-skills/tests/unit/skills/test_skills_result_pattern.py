"""Tests for Result pattern in skills executor."""

import pytest
from lexigram.contracts.ai.exceptions import SkillError
from lexigram.ai.skills.services.result_pattern_service import SkillExecutorWithResultPattern

class TestSkillExecutorResultPattern:
    """Test Result pattern in skills executor."""

    @pytest.fixture
    def skill_executor(self) -> SkillExecutorWithResultPattern:
        """Create skill executor."""
        return SkillExecutorWithResultPattern()

    @pytest.mark.asyncio
    async def test_execute_returns_ok(self, skill_executor):
        """Verify execute returns Ok."""
        result = await skill_executor.execute("search", {"query": "Python"})
        assert result.is_ok()
        output = result.unwrap()
        assert "skill" in output

    @pytest.mark.asyncio
    async def test_execute_returns_err_for_empty_skill(self, skill_executor):
        """Verify execute returns Err for empty skill name."""
        result = await skill_executor.execute("", {})
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SkillError)
