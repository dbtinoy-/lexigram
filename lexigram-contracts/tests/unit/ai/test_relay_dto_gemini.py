"""Tests for the Gemini generateContent wire DTO."""
from __future__ import annotations

from lexigram.contracts.ai.relay.dto import GeminiContent, GeminiPart, GeminiRequest


class TestGeminiDto:
    def test_part_to_dict(self) -> None:
        part = GeminiPart(text="hi")
        assert part.to_dict() == {"text": "hi"}

    def test_content_to_dict(self) -> None:
        content = GeminiContent(role="user", parts=[GeminiPart(text="hi")])
        assert content.to_dict() == {"role": "user", "parts": [{"text": "hi"}]}

    def test_request_generation_config(self) -> None:
        request = GeminiRequest.from_dict(
            {"contents": [{"role": "user", "parts": [{"text": "hi"}]}]}
        )
        assert request.contents[0].role == "user"
        assert request.generation_config == {}

    def test_request_to_dict_omits_empty_generation_config(self) -> None:
        request = GeminiRequest(contents=[GeminiContent(role="user", parts=[GeminiPart(text="hi")])])
        data = request.to_dict()
        assert data == {"contents": [{"role": "user", "parts": [{"text": "hi"}]}]}