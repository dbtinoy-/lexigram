"""Unit tests for ChatPipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.result import Err, Ok
from lexigram_example_ai.domain.conversation import Conversation, MessageRole
from lexigram_example_ai.pipelines.chat_pipeline import (
    ChatPipeline,
    ChatRequest,
    ChatResponse,
)


class TestChatPipelineRun:
    """Tests for ChatPipeline.run()."""

    @pytest.mark.asyncio
    async def test_returns_ok_on_success(self, chat_pipeline, empty_conversation):
        """Pipeline returns Ok(ChatResponse) when the LLM completes."""
        request = ChatRequest(
            conversation=empty_conversation,
            user_message="Hello, world!",
        )

        result = await chat_pipeline.run(request)

        assert result.is_ok()
        response = result.unwrap()
        assert isinstance(response, ChatResponse)
        assert response.content == "This is a stub reply."
        assert response.model == "stub"
        assert response.conversation_id == empty_conversation.id

    @pytest.mark.asyncio
    async def test_returns_err_on_llm_failure(self, empty_conversation, mock_token_counter):
        """Pipeline propagates Err when the LLM returns an error."""
        from lexigram.contracts.ai.exceptions import LLMError

        failing_llm = MagicMock()
        failing_llm.complete = AsyncMock(
            return_value=Err(LLMError("rate limit exceeded"))
        )
        pipeline = ChatPipeline(
            llm=failing_llm,
            token_counter=mock_token_counter,
        )

        request = ChatRequest(
            conversation=empty_conversation,
            user_message="trigger error",
        )

        result = await pipeline.run(request)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), LLMError)

    @pytest.mark.asyncio
    async def test_history_included_in_messages(
        self, mock_llm, mock_token_counter, empty_conversation
    ):
        """Prior conversation messages are forwarded to the LLM."""
        empty_conversation.add_message(role=MessageRole.USER, content="prior turn")
        empty_conversation.add_message(role=MessageRole.ASSISTANT, content="prior reply")

        pipeline = ChatPipeline(
            llm=mock_llm,
            token_counter=mock_token_counter,
            history_token_budget=1000,
        )
        request = ChatRequest(
            conversation=empty_conversation,
            user_message="new question",
        )

        await pipeline.run(request)

        call_args = mock_llm.complete.call_args
        messages = call_args[0][0]
        contents = [m.content for m in messages]
        # system + 2 history + new user = 4
        assert len(messages) >= 3
        assert "prior turn" in contents
        assert "new question" in contents

    @pytest.mark.asyncio
    async def test_history_trimmed_when_over_budget(self, mock_llm, empty_conversation):
        """Old history messages are dropped when the token budget is exceeded."""
        # very small budget forces trimming
        tiny_counter = MagicMock()
        tiny_counter.count = MagicMock(return_value=1)
        tiny_counter.count_messages = MagicMock(side_effect=lambda msgs: len(msgs) * 100)

        pipeline = ChatPipeline(
            llm=mock_llm,
            token_counter=tiny_counter,
            history_token_budget=50,  # forces trimming of all but last message
        )

        for i in range(10):
            empty_conversation.add_message(role=MessageRole.USER, content=f"turn {i}")
            empty_conversation.add_message(role=MessageRole.ASSISTANT, content=f"reply {i}")

        request = ChatRequest(
            conversation=empty_conversation,
            user_message="final question",
        )

        result = await pipeline.run(request)

        assert result.is_ok()
        call_args = mock_llm.complete.call_args
        messages = call_args[0][0]
        # system (1) + trimmed history + new user (1) — total much less than 20+2
        assert len(messages) < 20

    @pytest.mark.asyncio
    async def test_system_prompt_always_first(self, chat_pipeline, empty_conversation):
        """The system prompt is always the first message sent to the LLM."""
        request = ChatRequest(
            conversation=empty_conversation,
            user_message="test",
            system_prompt="Custom system instructions.",
        )

        await chat_pipeline.run(request)

        messages = mock_messages = chat_pipeline._llm.complete.call_args[0][0]
        assert messages[0].content == "Custom system instructions."

    @pytest.mark.asyncio
    async def test_empty_conversation_works(self, chat_pipeline):
        """Chat pipeline handles an empty conversation without errors."""
        conv = Conversation.start()
        request = ChatRequest(conversation=conv, user_message="first message")

        result = await chat_pipeline.run(request)

        assert result.is_ok()


__all__: list[str] = []
