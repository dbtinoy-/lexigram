"""Tests for the Claude Messages wire DTO."""
from __future__ import annotations

from lexigram.contracts.ai.relay.dto import ClaudeContent, ClaudeMessage, ClaudeRequest


class TestClaudeDto:
    def test_text_content_block(self) -> None:
        block = ClaudeContent.from_dict({"type": "text", "text": "hi"})
        assert block.type == "text"
        assert block.text == "hi"

    def test_message_to_dict(self) -> None:
        message = ClaudeMessage(
            role="user",
            content=[ClaudeContent(type="text", text="hi")],
        )
        data = message.to_dict()
        assert data == {"role": "user", "content": [{"type": "text", "text": "hi"}]}

    def test_request_max_tokens_required(self) -> None:
        request = ClaudeRequest.from_dict(
            {"model": "claude-sonnet-4-5", "max_tokens": 1024,
             "messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]}
        )
        assert request.max_tokens == 1024
        assert request.stream is False

    def test_request_to_dict_omits_none(self) -> None:
        request = ClaudeRequest(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[ClaudeMessage(role="user", content=[ClaudeContent(type="text", text="hi")])],
        )
        data = request.to_dict()
        assert "system" not in data
        assert data["max_tokens"] == 1024