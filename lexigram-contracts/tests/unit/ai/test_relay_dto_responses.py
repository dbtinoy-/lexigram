"""Tests for the OpenAI Responses wire DTO."""
from __future__ import annotations

from lexigram.contracts.ai.relay.dto import (
    ResponsesItem,
    ResponsesRequest,
    ResponsesResponse,
)


class TestResponsesDto:
    def test_input_message_item(self) -> None:
        item = ResponsesItem.from_dict(
            {"type": "message", "role": "user",
             "content": [{"type": "input_text", "text": "hi"}]}
        )
        assert item.type == "message"
        assert item.role == "user"

    def test_request_to_dict(self) -> None:
        request = ResponsesRequest(model="gpt-4o", input=[])
        data = request.to_dict()
        assert data == {"model": "gpt-4o", "input": []}

    def test_response_to_dict(self) -> None:
        response = ResponsesResponse(
            id="resp_1",
            model="gpt-4o",
            output=[ResponsesItem(type="message", role="assistant")],
        )
        data = response.to_dict()
        assert data["id"] == "resp_1"
        assert data["output"][0]["type"] == "message"