"""Tests for AIProvider.chat() delegate method."""

from __future__ import annotations

import pytest


class TestAIProviderChat:
    """Tests for AIProvider.chat() delegate method."""

    @pytest.mark.asyncio
    async def test_chat_raises_without_llm_sub(self) -> None:
        from lexigram.ai.di.provider import AIProvider

        provider = AIProvider()
        with pytest.raises(RuntimeError, match="LLM client not configured"):
            await provider.chat([{"role": "user", "content": "hello"}])

    @pytest.mark.asyncio
    async def test_chat_delegates_to_llm_client(self) -> None:
        from unittest.mock import AsyncMock, MagicMock
        from lexigram.ai.di.provider import AIProvider

        provider = AIProvider()
        mock_llm_sub = MagicMock()
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value="response")
        mock_llm_sub._llm_client = mock_client
        provider._llm_sub = mock_llm_sub

        result = await provider.chat(
            [{"role": "user", "content": "hello"}],
            tools=None,
        )

        mock_client.complete.assert_awaited_once()
        assert result == "response"
