"""Tests for the OpenAI Chat Completions request/response mapper."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.base import FormatMapper
from lexigram.ai.relay.mappers.openai_chat import OpenAIChatMapper
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.llm import FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import (
    OpenAIChatMessage,
    OpenAIChatRequest,
    OpenAIChatResponse,
)
from lexigram.contracts.ai.relay.types import RelayFormat

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


