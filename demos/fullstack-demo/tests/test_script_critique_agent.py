from unittest.mock import AsyncMock

import pytest
from lexigram.contracts.ai.llm import Completion
from lexigram.result import Ok

from shorts_creator.services.critique_tools import create_critique_tools
from shorts_creator.services.script_critique_agent import ScriptCritiqueAgent


class TestScriptCritiqueAgent:
    @pytest.mark.asyncio
    async def test_agent_has_name_and_tools(self):
        mock_llm = AsyncMock()
        tools = create_critique_tools(mock_llm)
        agent = ScriptCritiqueAgent(tools, mock_llm)

        assert agent.name == "script_critique"
        assert len(agent.tools) == 2
        assert agent.system_prompt

    @pytest.mark.asyncio
    async def test_critique_script_aggregates_results(self):
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(
            side_effect=[
                Ok(
                    Completion(
                        content='{"passed": true, "issues": [], "suggestions": ["Add a pause"], "score": 0.9, "details": "Good pacing"}',
                        model="fake",
                    )
                ),
                Ok(
                    Completion(
                        content='{"passed": false, "issues": ["Script too long"], "suggestions": ["Trim words"], "score": 0.3, "details": "Too many words"}',
                        model="fake",
                    )
                ),
            ]
        )
        tools = create_critique_tools(mock_llm)
        agent = ScriptCritiqueAgent(tools, mock_llm)

        result = await agent.critique_script("Some script text", target_duration=30.0)

        assert result.passed is False
        assert "Script too long" in result.issues
        assert result.score <= 0.6
        assert result.details is not None

    @pytest.mark.asyncio
    async def test_dev_mode_returns_pass(self):
        tools = create_critique_tools(None)
        agent = ScriptCritiqueAgent(tools, None)

        result = await agent.critique_script("Any script", target_duration=30.0)

        assert result.passed is True
        assert result.score == 1.0
