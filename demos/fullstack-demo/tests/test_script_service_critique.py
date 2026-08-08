from unittest.mock import AsyncMock

import pytest
from lexigram.contracts.ai.llm import Completion
from lexigram.result import Ok

from shorts_creator.services.critique_tools import CritiqueResult, create_critique_tools
from shorts_creator.services.script_critique_agent import ScriptCritiqueAgent
from shorts_creator.services.script_service import ScriptService


class TestScriptServiceCritique:
    @pytest.mark.asyncio
    async def test_service_critique_script_delegates_to_agent(self):
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(
            side_effect=[
                Ok(
                    Completion(
                        content='{"passed": true, "issues": [], "suggestions": [], "score": 0.9, "details": "Fine"}',
                        model="fake",
                    )
                ),
                Ok(
                    Completion(
                        content='{"passed": false, "issues": ["Too long"], "suggestions": ["Trim"], "score": 0.3, "details": "Too many words"}',
                        model="fake",
                    )
                ),
            ]
        )
        tools = create_critique_tools(mock_llm)
        agent = ScriptCritiqueAgent(tools, mock_llm)
        service = ScriptService()
        service.critique_agent = agent

        result = await service.critique_script("Some script text", target_duration=30.0)

        assert isinstance(result, CritiqueResult)
        assert result.passed is False
        assert "Too long" in result.issues

    @pytest.mark.asyncio
    async def test_service_no_agent_returns_pass(self):
        service = ScriptService()
        service.critique_agent = None

        result = await service.critique_script("Some script", target_duration=30.0)

        assert result.passed is True
        assert result.score == 1.0
