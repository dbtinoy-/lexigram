"""Tests for Ollama provider."""

from unittest.mock import AsyncMock, MagicMock

from lexigram.validation import SecretStr
import pytest

pytest.importorskip("ollama")

from lexigram.ai.llm.config import ClientConfig
from lexigram.ai.llm.clients.ollama import OllamaClient
from lexigram.ai.llm.types import ChatMessage, Role, StreamChunk


@pytest.mark.asyncio
async def test_complete_and_streaming(monkeypatch):
    config = ClientConfig(provider="ollama", model="m", api_key=SecretStr("x"))
    client = OllamaClient(config)

    # fake chat response
    fake_chat = AsyncMock(
        return_value={
            "message": {"content": "hello"},
            "model": "m",
            "prompt_eval_count": 1,
            "eval_count": 2,
        },
    )
    client.client = MagicMock()
    client.client.chat = fake_chat

    res = await client.complete([ChatMessage(role=Role.USER, content="hi")])
    assert res.is_ok()
    completion = res.unwrap()
    assert completion.content == "hello"

    # streaming: client.chat returns an async iterable when awaited
    async def stream_gen():
        for chunk in [
            {"message": {"content": "h"}, "model": "m"},
            {"message": {"content": "i"}, "model": "m", "done": True},
        ]:
            yield chunk

    client.client.chat = AsyncMock(return_value=stream_gen())

    chunks = []
    stream = client.stream_chat(
        [ChatMessage(role=Role.USER, content="hi")], model="m",
    )
    async for c in stream:
        assert isinstance(c, StreamChunk)
        chunks.append(c.delta)

    assert chunks == ["h", "i"]
