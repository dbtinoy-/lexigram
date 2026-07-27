from unittest.mock import AsyncMock

import pytest
from lexigram.contracts.ai.llm import Completion
from lexigram.result import Ok

from shorts_creator.services.critique_tools import (
    CritiqueResult,
    create_critique_tools,
)


class TestCritiqueTools:
    @pytest.mark.asyncio
    async def test_check_pacing_returns_result(self):
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(
            return_value=Ok(
                Completion(
                    content='{"passed": true, "issues": [], "suggestions": [], "score": 0.8, "details": "Good pacing"}',
                    model="fake",
                )
            )
        )
        tools = create_critique_tools(mock_llm)

        result = await tools["check_pacing"].execute(script_text="Hello world this is a script")

        assert isinstance(result, CritiqueResult)
        assert result.passed is True
        assert result.score == 0.8

    @pytest.mark.asyncio
    async def test_check_duration_returns_result(self):
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(
            return_value=Ok(
                Completion(
                    content='{"passed": false, "issues": ["Script too long for 30s"], "suggestions": ["Trim to 80 words"], "score": 0.3, "details": "Too many words"}',
                    model="fake",
                )
            )
        )
        tools = create_critique_tools(mock_llm)

        result = await tools["check_duration"].execute(
            script_text="Long script " * 50, target_duration=30.0
        )

        assert isinstance(result, CritiqueResult)
        assert result.passed is False
        assert len(result.issues) == 1

    @pytest.mark.asyncio
    async def test_language_model_receives_chat_messages_list(self):
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(
            return_value=Ok(
                Completion(
                    content='{"passed": true, "issues": [], "suggestions": [], "score": 1.0}',
                    model="fake",
                )
            )
        )
        tools = create_critique_tools(mock_llm)

        await tools["check_pacing"].execute(script_text="Body text")

        messages = mock_llm.complete.call_args.args[0]
        assert isinstance(messages, list)
        assert messages[0].role == "user"
        assert "Body text" in messages[0].content

    @pytest.mark.asyncio
    async def test_dev_mode_returns_pass(self):
        tools = create_critique_tools(None)

        result = await tools["check_pacing"].execute(script_text="Any text")

        assert result.passed is True
        assert result.score == 1.0
        assert len(result.issues) == 0

    def test_tools_are_function_tool_instances(self):
        from lexigram.ai.agents.tools.decorator import FunctionTool

        tools = create_critique_tools(None)

        assert isinstance(tools["check_pacing"], FunctionTool)
        assert isinstance(tools["check_duration"], FunctionTool)
        assert tools["check_pacing"].name == "check_pacing"
        assert tools["check_duration"].name == "check_duration"
