"""Tests for the OpenAI Chat Completions request/response mapper."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.base import FormatMapper
from lexigram.ai.relay.mappers.openai_chat import OpenAIChatMapper
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import (
    OpenAIChatChoice,
    OpenAIChatMessage,
    OpenAIChatRequest,
    OpenAIChatResponse,
    OpenAIChatStreamChunk,
)
from lexigram.contracts.ai.relay.ir import RelayRequest, RelayResponse, StreamState
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


def test_mapper_implements_format_mapper_protocol() -> None:
    """The OpenAI Chat mapper satisfies the FormatMapper protocol."""
    assert isinstance(mapper, FormatMapper)
    assert mapper.format is RelayFormat.OPENAI_CHAT


# ---------------------------------------------------------------------------
# request_to_ir
# ---------------------------------------------------------------------------


def test_request_system_messages_normalized_to_system_field(ctx: ConversionContext) -> None:
    """System messages land in the canonical system field, not messages."""
    request = make_request(
        messages=[
            make_message("system", content="You are helpful."),
            make_message("user", content="Hello"),
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.system == "You are helpful."
    assert [m.role for m in ir.messages] == ["user"]
    assert ir.messages[0].content == "Hello"


def test_request_multimodal_user_content(ctx: ConversionContext) -> None:
    """String and multimodal content map to canonical parts."""
    request = make_request(
        messages=[
            make_message(
                "user",
                content=[
                    {"type": "text", "text": "what is in"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://x/i.png", "detail": "high"},
                    },
                ],
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    content = ir.messages[0].content
    assert content == [
        TextPart(text="what is in"),
        ImageUrlPart(url="https://x/i.png", detail="high"),
    ]


def test_request_assistant_tool_calls(ctx: ConversionContext) -> None:
    """Assistant tool calls map to canonical ToolCall objects."""
    request = make_request(
        messages=[
            make_message(
                "assistant",
                content=None,
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_weather", "arguments": '{"city": "SF"}'},
                    }
                ],
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    message = ir.messages[0]
    assert message.role == "assistant"
    assert message.content == ""
    assert message.tool_calls == [
        ToolCall(
            id="call_1",
            type="function",
            function=FunctionCall(name="get_weather", arguments='{"city": "SF"}'),
        )
    ]


def test_request_tool_results(ctx: ConversionContext) -> None:
    """Tool results preserve role and tool_call_id."""
    request = make_request(
        messages=[make_message("tool", content="72F", tool_call_id="call_1")]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    message = ir.messages[0]
    assert message.role == "tool"
    assert message.tool_call_id == "call_1"
    assert message.content == "72F"


def test_request_tools_and_tool_choice(ctx: ConversionContext) -> None:
    """Tool definitions and tool choice map to canonical IR."""
    request = make_request(
        messages=[make_message("user", content="hi")],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Current weather",
                    "parameters": {"type": "object"},
                },
            }
        ],
        tool_choice="auto",
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.tools == [
        ToolDefinition(
            name="get_weather",
            description="Current weather",
            parameters={"type": "object"},
        )
    ]
    assert ir.tool_choice == "auto"


def test_request_response_format(ctx: ConversionContext) -> None:
    """Response format survives conversion."""
    request = make_request(
        messages=[make_message("user", content="hi")],
        response_format={"type": "json_object"},
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.response_format == {"type": "json_object"}


def test_request_zero_temperature_and_false_stream_survive(ctx: ConversionContext) -> None:
    """Explicit zero temperature and false stream are preserved."""
    request = make_request(
        messages=[make_message("user", content="hi")],
        temperature=0.0,
        stream=False,
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.temperature == 0.0
    assert ir.stream is False


def test_request_stop_string_and_list(ctx: ConversionContext) -> None:
    """A stop string normalizes to a one-element list; lists are preserved."""
    request = make_request(messages=[make_message("user", content="hi")], stop="END")
    assert mapper.request_to_ir(request, context=ctx).unwrap().stop_sequences == ["END"]
    request = make_request(
        messages=[make_message("user", content="hi")], stop=["A", "B"]
    )
    assert mapper.request_to_ir(request, context=ctx).unwrap().stop_sequences == [
        "A",
        "B",
    ]


def test_request_include_usage(ctx: ConversionContext) -> None:
    """stream_options.include_usage maps to the canonical include_usage flag."""
    request = make_request(
        messages=[make_message("user", content="hi")],
        stream=True,
        stream_options={"include_usage": True},
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.stream is True
    assert ir.include_usage is True


def test_request_reasoning_fields(ctx: ConversionContext) -> None:
    """OpenAI reasoning config maps to canonical thinking config."""
    request = make_request(
        messages=[make_message("user", content="hi")],
        reasoning={"effort": "high"},
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.thinking is not None
    assert ir.thinking.effort == "high"


def test_request_unknown_passthrough_preserved(ctx: ConversionContext) -> None:
    """Unknown request fields survive in canonical passthrough."""
    request = make_request(
        messages=[make_message("user", content="hi")],
        passthrough={"user": "abc", "seed": 123},
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.passthrough == {"user": "abc", "seed": 123}


def test_request_max_tokens_only(ctx: ConversionContext) -> None:
    """max_tokens alone becomes the canonical max_tokens."""
    request = make_request(
        messages=[make_message("user", content="hi")], max_tokens=100
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.max_tokens == 100


def test_request_max_completion_tokens_only(ctx: ConversionContext) -> None:
    """max_completion_tokens alone becomes the canonical max_tokens."""
    request = make_request(
        messages=[make_message("user", content="hi")], max_completion_tokens=200
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.max_tokens == 200


def test_request_max_tokens_equal_no_loss(ctx: ConversionContext) -> None:
    """Matching max_tokens/max_completion_tokens record no loss."""
    request = make_request(
        messages=[make_message("user", content="hi")],
        max_tokens=150,
        max_completion_tokens=150,
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.max_tokens == 150
    assert ctx.losses == []


def test_request_max_tokens_conflict_records_loss(ctx: ConversionContext) -> None:
    """Conflicting token caps prefer max_completion_tokens and record a loss."""
    request = make_request(
        messages=[make_message("user", content="hi")],
        max_tokens=150,
        max_completion_tokens=300,
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.max_tokens == 300
    assert len(ctx.losses) == 1
    assert ctx.losses[0].field == "max_completion_tokens"
    assert ctx.losses[0].reason == "conflicts_with_max_tokens"
    assert ctx.losses[0].target is RelayFormat.OPENAI_CHAT


def test_request_wrong_type_returns_unsupported_format(ctx: ConversionContext) -> None:
    """A non-request payload is rejected as unsupported_format."""
    response = OpenAIChatResponse(id="chatcmpl-1", model="gpt-4o", choices=[])
    result = mapper.request_to_ir(response, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value


# ---------------------------------------------------------------------------
# ir_to_request
# ---------------------------------------------------------------------------


def test_ir_to_request_prepends_system(ctx: ConversionContext) -> None:
    """The canonical system field becomes a leading system message."""
    ir = RelayRequest(
        model="gpt-4o",
        system="Be nice",
        messages=[ChatMessage(role="user", content="Hello")],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert isinstance(request, OpenAIChatRequest)
    assert [m.role for m in request.messages] == ["system", "user"]
    assert request.messages[0].content == "Be nice"
    assert request.messages[1].content == "Hello"


def test_ir_to_request_multimodal_parts(ctx: ConversionContext) -> None:
    """Canonical parts map back to wire part dicts."""
    ir = RelayRequest(
        model="gpt-4o",
        messages=[
            ChatMessage(
                role="user",
                content=[TextPart(text="see"), ImageUrlPart(url="https://x/i.png")],
            )
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.messages[0].content == [
        {"type": "text", "text": "see"},
        {
            "type": "image_url",
            "image_url": {"url": "https://x/i.png", "detail": "auto"},
        },
    ]


def test_ir_to_request_tool_call_json_arguments(ctx: ConversionContext) -> None:
    """Tool-call arguments serialize as compact JSON strings."""
    ir = RelayRequest(
        model="gpt-4o",
        messages=[
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        type="function",
                        function=FunctionCall(name="get_weather", arguments={"city": "SF"}),
                    )
                ],
            )
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    tool_call = request.messages[0].tool_calls[0]
    assert tool_call["id"] == "call_1"
    assert tool_call["function"]["name"] == "get_weather"
    assert tool_call["function"]["arguments"] == '{"city":"SF"}'


def test_ir_to_request_temperature_stream_usage(ctx: ConversionContext) -> None:
    """Zero temperature, stream, and include_usage survive roundtrip."""
    ir = RelayRequest(
        model="gpt-4o",
        messages=[ChatMessage(role="user", content="hi")],
        temperature=0.0,
        stream=True,
        include_usage=True,
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.temperature == 0.0
    assert request.stream is True
    assert request.stream_options == {"include_usage": True}


def test_ir_to_request_stop_sequences(ctx: ConversionContext) -> None:
    """Canonical stop sequences map back to a wire stop list."""
    ir = RelayRequest(
        model="gpt-4o",
        messages=[ChatMessage(role="user", content="hi")],
        stop_sequences=["A", "B"],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.stop == ["A", "B"]


# ---------------------------------------------------------------------------
# response_to_ir
# ---------------------------------------------------------------------------


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
    """Missing id/created default to empty/zero without nulls."""
    ir = RelayResponse(model="gpt-4o")
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.id == ""
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
    }


def test_ir_to_response_no_usage_when_none(ctx: ConversionContext) -> None:
    """None usage is omitted from the wire response."""
    ir = RelayResponse(model="gpt-4o", content="Hi")
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.usage is None


def test_ir_to_response_thinking_roundtrip(ctx: ConversionContext) -> None:
    """Thinking content is preserved as message reasoning passthrough."""
    ir = RelayResponse(
        model="gpt-4o",
        content="Hi",
        thinking=ThinkingResult(content="thoughts"),
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.choices[0].message.passthrough["reasoning"] == "thoughts"


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
