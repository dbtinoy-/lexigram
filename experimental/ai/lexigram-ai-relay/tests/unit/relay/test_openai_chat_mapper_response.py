"""Response-direction tests for the OpenAI Chat Completions mapper."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.openai_chat import OpenAIChatMapper
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.llm import FunctionCall, ToolCall
from lexigram.contracts.ai.relay.dto import (
    OpenAIChatChoice,
    OpenAIChatMessage,
    OpenAIChatRequest,
    OpenAIChatResponse,
    OpenAIChatStreamChunk,
)
from lexigram.contracts.ai.relay.ir import RelayResponse, StreamState
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.ai.thinking import ThinkingResult

mapper = OpenAIChatMapper()


def make_request(**kwargs: Any) -> OpenAIChatRequest:
    """Build a request with sensible defaults."""
    defaults: dict[str, Any] = {"model": "gpt-4o", "messages": []}
    defaults.update(kwargs)
    return OpenAIChatRequest(**defaults)


def make_message(role: str, **kwargs: Any) -> OpenAIChatMessage:
    """Build a message with a default role."""
    defaults: dict[str, Any] = {"role": role}
    defaults.update(kwargs)
    return OpenAIChatMessage(**defaults)


@pytest.fixture
def ctx() -> ConversionContext:
    """A fresh conversion context per test."""
    return ConversionContext()


def test_response_text_and_finish(ctx: ConversionContext) -> None:
    """Text completion maps to content, id, model, created, finish reason."""
    response = OpenAIChatResponse(
        id="chatcmpl-1",
        model="gpt-4o",
        created=123,
        choices=[
            OpenAIChatChoice(
                index=0,
                message=make_message("assistant", content="Hi"),
                finish_reason="stop",
            )
        ],
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.id == "chatcmpl-1"
    assert ir.model == "gpt-4o"
    assert ir.created == 123
    assert ir.content == "Hi"
    assert ir.finish_reason == "stop"


def test_response_reasoning_content(ctx: ConversionContext) -> None:
    """Reasoning passthrough on the message maps to ThinkingResult."""
    response = OpenAIChatResponse(
        id="chatcmpl-1",
        model="gpt-4o",
        choices=[
            OpenAIChatChoice(
                index=0,
                message=make_message(
                    "assistant", content="", passthrough={"reasoning": "thoughts"}
                ),
            )
        ],
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.thinking is not None
    assert ir.thinking.content == "thoughts"


def test_response_tool_calls(ctx: ConversionContext) -> None:
    """Tool calls in the response map to canonical ToolCall objects."""
    response = OpenAIChatResponse(
        id="chatcmpl-1",
        model="gpt-4o",
        choices=[
            OpenAIChatChoice(
                index=0,
                message=make_message(
                    "assistant",
                    content=None,
                    tool_calls=[
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "f", "arguments": '{"a": 1}'},
                        }
                    ],
                ),
            )
        ],
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.tool_calls == [
        ToolCall(id="c1", type="function", function=FunctionCall(name="f", arguments='{"a": 1}'))
    ]


def test_response_mixed_text_and_tool_calls(ctx: ConversionContext) -> None:
    """Content and tool calls coexist on one response."""
    response = OpenAIChatResponse(
        id="chatcmpl-1",
        model="gpt-4o",
        choices=[
            OpenAIChatChoice(
                index=0,
                message=make_message(
                    "assistant",
                    content="Let me check.",
                    tool_calls=[
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "f", "arguments": "{}"},
                        }
                    ],
                ),
            )
        ],
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == "Let me check."
    assert len(ir.tool_calls) == 1


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        ("stop", "stop"),
        ("length", "length"),
        ("tool_calls", "tool_calls"),
        ("function_call", "function_call"),
        ("content_filter", "content_filter"),
        ("", None),
    ],
)
def test_response_finish_reasons_normalized(
    ctx: ConversionContext, raw: str, canonical: str | None
) -> None:
    """All OpenAI finish reasons normalize to canonical values."""
    response = OpenAIChatResponse(
        id="chatcmpl-1",
        model="gpt-4o",
        choices=[
            OpenAIChatChoice(
                index=0,
                message=make_message("assistant", content="Hi"),
                finish_reason=raw,
            )
        ],
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason == canonical


def test_response_usage_details(ctx: ConversionContext) -> None:
    """Usage sub-details map into RelayUsage."""
    response = OpenAIChatResponse(
        id="chatcmpl-1",
        model="gpt-4o",
        choices=[],
        usage={
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "prompt_tokens_details": {"cached_tokens": 3},
            "completion_tokens_details": {"reasoning_tokens": 2},
        },
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.usage == RelayUsage(
        prompt_tokens=10,
        completion_tokens=5,
        cache_read_tokens=3,
        reasoning_tokens=2,
    )


def test_response_empty_choices(ctx: ConversionContext) -> None:
    """Empty choices yield an empty canonical response without crash."""
    response = OpenAIChatResponse(id="chatcmpl-1", model="gpt-4o", choices=[])
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == ""
    assert ir.finish_reason is None
    assert ir.id == "chatcmpl-1"


def test_response_unknown_and_system_fingerprint(ctx: ConversionContext) -> None:
    """Unknown fields and system fingerprint survive in passthrough."""
    response = OpenAIChatResponse(
        id="chatcmpl-1",
        model="gpt-4o",
        choices=[],
        system_fingerprint="fp_abc",
        passthrough={"x_req_id": "r"},
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.passthrough == {"system_fingerprint": "fp_abc", "x_req_id": "r"}


def test_response_no_usage(ctx: ConversionContext) -> None:
    """Absent usage maps to None."""
    response = OpenAIChatResponse(
        id="chatcmpl-1",
        model="gpt-4o",
        choices=[
            OpenAIChatChoice(
                index=0, message=make_message("assistant", content="Hi")
            )
        ],
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.usage is None


def test_response_wrong_type_returns_unsupported_format(ctx: ConversionContext) -> None:
    """A non-response payload is rejected as unsupported_format."""
    request = make_request(messages=[make_message("user", content="hi")])
    result = mapper.response_to_ir(request, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value


# ---------------------------------------------------------------------------
# ir_to_response
# ---------------------------------------------------------------------------


def test_ir_to_response_builds_valid_response(ctx: ConversionContext) -> None:
    """Canonical response maps to a valid Chat Completions response."""
    ir = RelayResponse(
        model="gpt-4o",
        id="chatcmpl-1",
        created=123,
        content="Hi",
        finish_reason="stop",
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert isinstance(response, OpenAIChatResponse)
    assert response.id == "chatcmpl-1"
    assert response.object == "chat.completion"
    assert response.model == "gpt-4o"
    assert response.created == 123
    assert response.choices[0].message.content == "Hi"
    assert response.choices[0].finish_reason == "stop"


def test_ir_to_response_defaults(ctx: ConversionContext) -> None:
    """Missing id defaults to a generated id without nulls."""
    ir = RelayResponse(model="gpt-4o")
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.id.startswith("chatcmpl-")
    assert response.created == 0
    assert response.choices[0].message.content is None
    assert response.choices[0].finish_reason is None


def test_ir_to_response_tool_only_no_content(ctx: ConversionContext) -> None:
    """Tool-only turns omit content and emit JSON argument strings."""
    ir = RelayResponse(
        model="gpt-4o",
        content="",
        tool_calls=[
            ToolCall(
                id="c1",
                type="function",
                function=FunctionCall(name="get_weather", arguments={"city": "SF"}),
            )
        ],
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    message = response.choices[0].message
    assert message.content is None
    assert message.tool_calls == [
        {
            "id": "c1",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"city":"SF"}'},
        }
    ]


def test_ir_to_response_usage_reconstructed(ctx: ConversionContext) -> None:
    """RelayUsage reconstructs the wire usage dict with details."""
    ir = RelayResponse(
        model="gpt-4o",
        content="Hi",
        usage=RelayUsage(
            prompt_tokens=10,
            completion_tokens=5,
            cache_read_tokens=3,
            reasoning_tokens=2,
        ),
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.usage == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "prompt_tokens_details": {"cached_tokens": 3},
        "completion_tokens_details": {"reasoning_tokens": 2},
        "input_tokens": 0,
        "output_tokens": 0,
    }


def test_ir_to_response_no_usage_when_none(ctx: ConversionContext) -> None:
    """None usage is omitted from the wire response."""
    ir = RelayResponse(model="gpt-4o", content="Hi")
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.usage is None


def test_ir_to_response_thinking_roundtrip(ctx: ConversionContext) -> None:
    """Thinking content is not emitted as message reasoning passthrough."""
    ir = RelayResponse(
        model="gpt-4o",
        content="Hi",
        thinking=ThinkingResult(content="thoughts"),
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert "reasoning" not in response.choices[0].message.passthrough


def test_ir_to_response_system_fingerprint(ctx: ConversionContext) -> None:
    """System fingerprint restores from canonical passthrough."""
    ir = RelayResponse(
        model="gpt-4o",
        content="Hi",
        passthrough={"system_fingerprint": "fp_abc", "x_req_id": "r"},
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.system_fingerprint == "fp_abc"
    assert response.passthrough == {"x_req_id": "r"}


def test_stream_ops_unsupported_until_shared_lifecycle(ctx: ConversionContext) -> None:
    """Stream conversion is deferred to the shared stream lifecycle task."""
    state = StreamState(
        source=RelayFormat.OPENAI_CHAT,
        target=RelayFormat.OPENAI_CHAT,
        model="gpt-4o",
    )
    chunk = OpenAIChatStreamChunk(id="x", model="m", choices=[])
    result = mapper.stream_to_delta(chunk, state=state)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FEATURE.value
