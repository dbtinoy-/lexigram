"""Tests for the OpenAI Chat Completions wire DTO."""
from __future__ import annotations

from lexigram.contracts.ai.relay.dto import OpenAIChatMessage, OpenAIChatRequest


class TestOpenAIChatDto:
    def test_to_dict_string_content(self) -> None:
        message = OpenAIChatMessage(role="user", content="Hello")
        data = message.to_dict()
        assert data == {"role": "user", "content": "Hello"}

    def test_to_dict_preserves_passthrough(self) -> None:
        message = OpenAIChatMessage(
            role="assistant",
            content="Hi",
            passthrough={"refusal": None},
        )
        data = message.to_dict()
        assert data["refusal"] is None

    def test_from_dict_drops_none_optional_fields(self) -> None:
        request = OpenAIChatRequest.from_dict(
            {"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]}
        )
        assert request.temperature is None
        assert request.max_tokens is None

    def test_request_to_dict_omits_none(self) -> None:
        request = OpenAIChatRequest(
            model="gpt-4o",
            messages=[OpenAIChatMessage(role="user", content="hi")],
        )
        data = request.to_dict()
        assert data == {"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]}

    def test_request_to_dict_keeps_explicit_zero(self) -> None:
        request = OpenAIChatRequest(
            model="gpt-4o",
            messages=[],
            temperature=0.0,
        )
        data = request.to_dict()
        assert data["temperature"] == 0.0