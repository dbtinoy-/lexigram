"""Gemini mapper tests: canonical IR to wire response (``ir_to_response``)."""

from __future__ import annotations

import pytest

from gemini_mapper_test_helpers import mapper
from lexigram.ai.relay.context import ConversionContext
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.llm import FunctionCall, ToolCall
from lexigram.contracts.ai.relay.dto import GeminiResponse
from lexigram.contracts.ai.relay.ir import RelayResponse, StreamState
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.ai.thinking import ThinkingResult


def test_ir_to_response_text(ctx: ConversionContext) -> None:
    """Canonical content becomes a model candidate text part."""
    ir = RelayResponse(model="gemini-2.5-flash", content="Hi")
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert isinstance(response, GeminiResponse)
    assert response.candidates[0].content.role == "model"
    assert response.candidates[0].content.parts[0].text == "Hi"


def test_ir_to_response_thinking_signature_emitted(ctx: ConversionContext) -> None:
    """Thinking results do not emit thought parts on the wire."""
    ir = RelayResponse(
        model="gemini-2.5-flash",
        content="Answer",
        thinking=ThinkingResult(content="Think.", signature="sig1"),
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    parts = response.candidates[0].content.parts
    assert len(parts) == 1
    assert parts[0].text == "Answer"
    assert parts[0].thought is False


def test_ir_to_response_tool_call(ctx: ConversionContext) -> None:
    """Tool calls become functionCall parts."""
    ir = RelayResponse(
        model="gemini-2.5-flash",
        tool_calls=[
            ToolCall(
                id="w",
                type="custom",
                function=FunctionCall(name="w", arguments={"q": 1}),
            )
        ],
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.candidates[0].content.parts[0].function_call == {
        "name": "w",
        "args": {"q": 1},
    }


@pytest.mark.parametrize(
    ("canonical", "wire"),
    [
        ("stop", "STOP"),
        ("length", "MAX_TOKENS"),
        ("content_filter", "SAFETY"),
        ("tool_calls", "STOP"),
        ("function_call", "STOP"),
        ("other", "OTHER"),
    ],
)
def test_ir_to_response_finish_reasons(
    ctx: ConversionContext, canonical: str, wire: str
) -> None:
    """Canonical finish reasons map back to Gemini values."""
    ir = RelayResponse(model="gemini-2.5-flash", content="x", finish_reason=canonical)
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.candidates[0].finish_reason == wire


def test_ir_to_response_usage(ctx: ConversionContext) -> None:
    """RelayUsage maps back to usageMetadata."""
    ir = RelayResponse(
        model="gemini-2.5-flash",
        content="x",
        usage=RelayUsage(
            prompt_tokens=100,
            completion_tokens=20,
            cache_read_tokens=30,
            reasoning_tokens=5,
        ),
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    usage = response.usage_metadata
    assert usage is not None
    assert usage.prompt_token_count == 100
    assert usage.candidates_token_count == 20
    assert usage.total_token_count == 120
    assert usage.cached_content_token_count == 0
    assert usage.thoughts_token_count == 0


def test_ir_to_response_passthrough_roundtrip(ctx: ConversionContext) -> None:
    """Provider metadata round-trips through passthrough keys."""
    ir = RelayResponse(
        model="gemini-2.5-flash",
        content="x",
        id="resp_1",
        passthrough={
            "model_version": "gemini-2.5-flash-001",
            "prompt_feedback": {"blockReason": "SAFETY"},
            "create_time": "2026-01-01T00:00:00Z",
        },
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.response_id is None
    assert response.model_version == "gemini-2.5-flash-001"
    assert response.prompt_feedback is not None
    assert response.prompt_feedback.block_reason == "SAFETY"
    assert response.create_time == "2026-01-01T00:00:00Z"


def test_ir_to_response_defaults(ctx: ConversionContext) -> None:
    """An empty canonical response yields a minimal candidate."""
    ir = RelayResponse(model="gemini-2.5-flash")
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert len(response.candidates) == 1
    assert response.candidates[0].finish_reason is None


def test_stream_ops_unsupported_until_shared_lifecycle(ctx: ConversionContext) -> None:
    """Stream conversion is deferred to the shared stream lifecycle task."""
    event = GeminiResponse()
    state = StreamState(
        source=RelayFormat.GEMINI,
        target=RelayFormat.GEMINI,
        model="gemini-2.5-flash",
    )
    result = mapper.stream_to_delta(event, state=state)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FEATURE.value
