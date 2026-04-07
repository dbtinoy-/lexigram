"""Tests for Result pattern in agent executor."""

import pytest
from lexigram.contracts.ai.agents import AgentError
from lexigram.ai.agents.services.result_pattern_service import AgentExecutorWithResultPattern

class TestAgentExecutorResultPattern:
    """Test Result pattern in agent executor."""

    @pytest.fixture
    def agent_executor(self) -> AgentExecutorWithResultPattern:
        """Create agent executor."""
        return AgentExecutorWithResultPattern()

    @pytest.mark.asyncio
    async def test_execute_returns_ok(self, agent_executor):
        """Verify execute returns Ok."""
        result = await agent_executor.execute("researcher", "Find Python docs", ["search", "summarize"])
        assert result.is_ok()
        output = result.unwrap()
        assert "agent" in output

    @pytest.mark.asyncio
    async def test_execute_returns_err_for_empty_agent(self, agent_executor):
        """Verify execute returns Err for empty agent name."""
        result = await agent_executor.execute("", "task")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), AgentError)

    @pytest.mark.asyncio
    async def test_execute_returns_err_for_empty_task(self, agent_executor):
        """Verify execute returns Err for empty task."""
        result = await agent_executor.execute("researcher", "")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), AgentError)
