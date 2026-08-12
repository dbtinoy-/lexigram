"""Tests for the OpenAI Responses request/response mapper."""

from __future__ import annotations

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.base import FormatMapper
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.relay.dto import ResponsesItem, ResponsesRequest, ResponsesResponse, ResponsesUsage
from lexigram.contracts.ai.relay.types import RelayFormat
from typing import Any

def resp_req(**kwargs: Any) -> ResponsesRequest:
    """Build a Responses request with sensible defaults."""
    defaults: dict[str, Any] = {"model": "gpt-5.2", "input": []}
    defaults.update(kwargs)
    return ResponsesRequest(**defaults)

def item(**kwargs: Any) -> ResponsesItem:
    """Build a Responses input item with sensible defaults."""
    defaults: dict[str, Any] = {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "hi"}],
    }
    defaults.update(kwargs)
    return ResponsesItem(**defaults)

def resp(**kwargs: Any) -> ResponsesResponse:
    """Build a Responses response with sensible defaults."""
    defaults: dict[str, Any] = {"id": "resp_1", "model": "gpt-5.2", "output": []}
    defaults.update(kwargs)
    return ResponsesResponse(**defaults)

def usage(**kwargs: Any) -> ResponsesUsage:
    """Build Responses usage with sensible defaults."""
    defaults: dict[str, Any] = {"input_tokens": 10, "output_tokens": 5}
    defaults.update(kwargs)
    return ResponsesUsage(**defaults)

def ctx() -> ConversionContext:
    """A fresh conversion context per test."""
    return ConversionContext()

def test_mapper_implements_format_mapper_protocol(*, mapper: OpenAIResponsesMapper) -> None:
    """The Responses mapper satisfies the FormatMapper protocol."""
    assert isinstance(mapper, FormatMapper)
    assert mapper.format is RelayFormat.OPENAI_RESPONSES

def test_wrong_request_type(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Non-Responses payloads are rejected as unsupported format."""
    result = mapper.request_to_ir({"model": "x"}, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value

def test_wrong_response_type(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Non-Responses payloads are rejected as unsupported format."""
    result = mapper.response_to_ir({"id": "x"}, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value
