"""Tests for the Anthropic Claude Messages request/response mapper."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.base import FormatMapper
from lexigram.ai.relay.mappers.claude import ClaudeMapper
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageBase64Part, ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import (
    ClaudeContent,
    ClaudeMessage,
    ClaudeRequest,
    ClaudeResponse,
    ClaudeUsage,
)
from lexigram.contracts.ai.relay.ir import RelayRequest, RelayResponse, StreamState
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.ai.thinking import ThinkingConfig, ThinkingResult
from lexigram.contracts.core.result import Ok

mapper = ClaudeMapper()


def claude_req(**kwargs: Any) -> ClaudeRequest:
    """Build a Claude request with sensible defaults."""
    defaults: dict[str, Any] = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 1024,
        "messages": [],
    }
    defaults.update(kwargs)
    return ClaudeRequest(**defaults)


def claude_msg(role: str, blocks: list[ClaudeContent]) -> ClaudeMessage:
    """Build a Claude message."""
    return ClaudeMessage(role=role, content=blocks)


@pytest.fixture
def ctx() -> ConversionContext:
    """A fresh conversion context per test."""
    return ConversionContext()


class FakeResolver:
    """Structural media resolver returning a fixed base64 payload."""

    def resolve(self, url: str) -> object:
        return Ok(("image/png", "AAAB"))


def test_mapper_implements_format_mapper_protocol() -> None:
    """The Claude mapper satisfies the FormatMapper protocol."""
    assert isinstance(mapper, FormatMapper)
    assert mapper.format is RelayFormat.CLAUDE


# ---------------------------------------------------------------------------
# request_to_ir
# ---------------------------------------------------------------------------


def test_request_system_field(ctx: ConversionContext) -> None:
    """The top-level system field maps to canonical IR system."""
    request = claude_req(
        system="You are helpful.",
        messages=[claude_msg("user", [ClaudeContent(text="Hello")])],
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.system == "You are helpful."
    assert ir.messages[0].content == "Hello"


def test_request_text_and_image_blocks(ctx: ConversionContext) -> None:
    """Text and base64 image blocks map to canonical content parts."""
    request = claude_req(
        messages=[
            claude_msg(
                "user",
                [
                    ClaudeContent(text="what is in"),
                    ClaudeContent(
                        type="image",
                        image_source={
                            "type": "base64",
                            "media_type": "image/png",
                            "data": "AAAB",
                        },
                    ),
                ],
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.messages[0].content == [
        TextPart(text="what is in"),
        ImageBase64Part(data="AAAB", media_type="image/png"),
    ]


def test_request_tool_result_blocks(ctx: ConversionContext) -> None:
    """Tool result blocks become canonical tool messages."""
    request = claude_req(
        messages=[
            claude_msg(
                "user",
                [
                    ClaudeContent(
                        type="tool_result",
                        tool_use_id="call_1",
                        tool_result_content=[ClaudeContent(text="72F")],
                    )
                ],
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    message = ir.messages[0]
    assert message.role == "tool"
    assert message.tool_call_id == "call_1"
    assert message.content == "72F"


def test_request_assistant_thinking_and_tool_use(ctx: ConversionContext) -> None:
    """Thinking blocks and tool_use blocks map into one assistant turn."""
    request = claude_req(
        messages=[
            claude_msg(
                "assistant",
                [
                    ClaudeContent(
                        type="thinking",
                        thinking="Let me think",
                        signature="sig123",
                    ),
                    ClaudeContent(text="Checking now."),
                    ClaudeContent(
                        type="tool_use",
                        tool_use_id="call_1",
                        name="get_weather",
                        input={"city": "SF"},
                    ),
                ],
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    message = ir.messages[0]
    assert message.role == "assistant"
    assert message.content == "Checking now."
    assert message.thinking_blocks == [
        {"type": "thinking", "thinking": "Let me think", "signature": "sig123"}
    ]
    assert message.tool_calls == [
        ToolCall(
            id="call_1",
            type="custom",
            function=FunctionCall(name="get_weather", arguments={"city": "SF"}),
        )
    ]


def test_request_tools_and_tool_choice(ctx: ConversionContext) -> None:
    """Claude tool definitions and tool choice map to canonical IR."""
    request = claude_req(
        messages=[claude_msg("user", [ClaudeContent(text="hi")])],
        tools=[
            {
                "name": "get_weather",
                "description": "Current weather",
                "input_schema": {"type": "object"},
            }
        ],
        tool_choice={"type": "auto"},
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.tools == [
        ToolDefinition(
            name="get_weather",
            description="Current weather",
            parameters={"type": "object"},
        )
    ]
    assert ir.tool_choice == {"type": "auto"}


def test_request_stop_stream_temperature(ctx: ConversionContext) -> None:
    """Stop sequences, stream, and temperature map to canonical IR."""
    request = claude_req(
        messages=[claude_msg("user", [ClaudeContent(text="hi")])],
        stop_sequences=["END"],
        stream=True,
        temperature=0.0,
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.stop_sequences == ["END"]
    assert ir.stream is True
    assert ir.temperature == 0.0


def test_request_thinking_config(ctx: ConversionContext) -> None:
    """Enabled thinking maps to canonical thinking budget config."""
    request = claude_req(
        messages=[claude_msg("user", [ClaudeContent(text="hi")])],
        thinking={"type": "enabled", "budget_tokens": 1234},
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.thinking == ThinkingConfig(budget_tokens=1234)


def test_request_max_tokens_carried_verbatim(ctx: ConversionContext) -> None:
    """The source max_tokens carries into canonical IR without rewriting."""
    request = claude_req(
        messages=[claude_msg("user", [ClaudeContent(text="hi")])],
        max_tokens=9999,
        thinking={"type": "enabled", "budget_tokens": 500},
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.max_tokens == 9999


def test_request_metadata_and_passthrough(ctx: ConversionContext) -> None:
    """Metadata and unknown fields survive in canonical IR."""
    request = claude_req(
        messages=[claude_msg("user", [ClaudeContent(text="hi")])],
        metadata={"user_id": "u1"},
        passthrough={"service_tier": "default"},
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.metadata == {"metadata": {"user_id": "u1"}}
    assert ir.passthrough == {"service_tier": "default"}


def test_request_wrong_type_returns_unsupported_format(ctx: ConversionContext) -> None:
    """A non-request payload is rejected as unsupported_format."""
    response = ClaudeResponse(id="msg_1", model="claude-sonnet-4-5")
    result = mapper.request_to_ir(response, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value


# ---------------------------------------------------------------------------
# ir_to_request
# ---------------------------------------------------------------------------


def test_ir_to_request_system(ctx: ConversionContext) -> None:
    """Canonical system becomes the Claude top-level system field."""
    ir = RelayRequest(
        model="claude-sonnet-4-5",
        system="Be nice",
        max_tokens=1024,
        messages=[ChatMessage(role="user", content="Hello")],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert isinstance(request, ClaudeRequest)
    assert request.system == [{"type": "text", "text": "Be nice"}]
    assert request.messages[0].role == "user"
    assert request.messages[0].content == "Hello"


def test_ir_to_request_text_and_tool_result(ctx: ConversionContext) -> None:
    """Canonical turns map back to Claude blocks."""
    ir = RelayRequest(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            ChatMessage(role="user", content="Hi"),
            ChatMessage(role="tool", content="72F", tool_call_id="call_1"),
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    tool_result = request.messages[1]
    assert tool_result.role == "user"
    assert tool_result.content[0].type == "tool_result"
    assert tool_result.content[0].tool_use_id == "call_1"
    assert tool_result.content[0].tool_result_content[0].text == "72F"


def test_ir_to_request_assistant_thinking_tool_use(ctx: ConversionContext) -> None:
    """Thinking blocks and tool calls map back to Claude assistant blocks."""
    ir = RelayRequest(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            ChatMessage(
                role="assistant",
                content="Checking now.",
                thinking_blocks=[
                    {
                        "type": "thinking",
                        "thinking": "Let me think",
                        "signature": "sig123",
                    }
                ],
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        type="custom",
                        function=FunctionCall(
                            name="get_weather", arguments={"city": "SF"}
                        ),
                    )
                ],
            )
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    blocks = request.messages[0].content
    assert blocks[0].type == "thinking"
    assert blocks[0].signature == "sig123"
    assert blocks[1].type == "text"
    assert blocks[1].text == "Checking now."
    assert blocks[2].type == "tool_use"
    assert blocks[2].tool_use_id == "call_1"
    assert blocks[2].input == {"city": "SF"}


def test_ir_to_request_image_base64(ctx: ConversionContext) -> None:
    """Canonical base64 image parts are dropped on the Claude hop."""
    ir = RelayRequest(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            ChatMessage(
                role="user",
                content=[
                    TextPart(text="see"),
                    ImageBase64Part(data="AAAB", media_type="image/png"),
                ],
            )
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.messages[0].content == []


def test_ir_to_request_url_image_requires_resolver(ctx: ConversionContext) -> None:
    """URL images without a media resolver are a media_resolution_required error."""
    ir = RelayRequest(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            ChatMessage(role="user", content=[ImageUrlPart(url="https://x/i.png")])
        ],
    )
    result = mapper.ir_to_request(ir, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.MEDIA_RESOLUTION_REQUIRED.value


def test_ir_to_request_url_image_resolved() -> None:
    """A media resolver converts a URL image into a base64 image block."""
    ctx = ConversionContext(media_resolver=FakeResolver())
    ir = RelayRequest(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            ChatMessage(role="user", content=[ImageUrlPart(url="https://x/i.png")])
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    image = request.messages[0].content[0]
    assert image.type == "image"
    assert image.image_source == {
        "type": "base64",
        "media_type": "image/png",
        "data": "AAAB",
    }


def test_ir_to_request_max_tokens_from_context() -> None:
    """Missing max_tokens falls back to the configured default."""
    ctx = ConversionContext(default_max_tokens=lambda _model: 4096)
    ir = RelayRequest(
        model="claude-sonnet-4-5",
        messages=[ChatMessage(role="user", content="hi")],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.max_tokens == 4096


def test_ir_to_request_max_tokens_missing_required_option(
    ctx: ConversionContext,
) -> None:
    """No max_tokens and no default is a missing_required_option error."""
    ir = RelayRequest(
        model="claude-sonnet-4-5",
        messages=[ChatMessage(role="user", content="hi")],
    )
    result = mapper.ir_to_request(ir, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.MISSING_REQUIRED_OPTION.value


def test_ir_to_request_thinking_config(ctx: ConversionContext) -> None:
    """Canonical thinking budget maps back to an enabled thinking dict."""
    ir = RelayRequest(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[ChatMessage(role="user", content="hi")],
        thinking=ThinkingConfig(budget_tokens=1234),
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.thinking == {"type": "enabled", "budget_tokens": 1234}


def test_ir_to_request_tools_tool_choice_stop(ctx: ConversionContext) -> None:
    """Tools, tool choice, and stop sequences map back to the wire."""
    ir = RelayRequest(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[ChatMessage(role="user", content="hi")],
        tools=[
            ToolDefinition(
                name="get_weather",
                description="Current weather",
                parameters={"type": "object"},
            )
        ],
        tool_choice={"type": "auto"},
        stop_sequences=["END"],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.tools == [
        {
            "name": "get_weather",
            "description": "Current weather",
            "input_schema": {"type": "object"},
        }
    ]
    assert request.tool_choice == {"type": "auto"}
    assert request.stop_sequences == ["END"]


def test_ir_to_request_zero_temperature(ctx: ConversionContext) -> None:
    """Explicit zero temperature survives on the wire."""
    ir = RelayRequest(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[ChatMessage(role="user", content="hi")],
        temperature=0.0,
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.temperature == 0.0


# ---------------------------------------------------------------------------
# response_to_ir
# ---------------------------------------------------------------------------


def test_response_text_thinking_signature(ctx: ConversionContext) -> None:
    """Text and thinking blocks map to content and ThinkingResult."""
    response = ClaudeResponse(
        id="msg_1",
        model="claude-sonnet-4-5",
        content=[
            ClaudeContent(type="thinking", thinking="think", signature="sig123"),
            ClaudeContent(text="Hi there"),
        ],
        stop_reason="end_turn",
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.id == "msg_1"
    assert ir.model == "claude-sonnet-4-5"
    assert ir.content == "Hi there"
    assert ir.thinking == ThinkingResult(content="think", signature="sig123")
    assert ir.finish_reason == "stop"
    assert ir.created is None


def test_response_tool_use(ctx: ConversionContext) -> None:
    """Tool use blocks map to canonical ToolCall objects."""
    response = ClaudeResponse(
        id="msg_1",
        model="claude-sonnet-4-5",
        content=[
            ClaudeContent(
                type="tool_use",
                tool_use_id="call_1",
                name="get_weather",
                input={"city": "SF"},
            )
        ],
        stop_reason="tool_use",
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == ""
    assert ir.tool_calls == [
        ToolCall(
            id="call_1",
            type="custom",
            function=FunctionCall(name="get_weather", arguments={"city": "SF"}),
        )
    ]
    assert ir.finish_reason == "tool_calls"


def test_response_tool_result(ctx: ConversionContext) -> None:
    """Tool result blocks map to canonical tool result messages."""
    response = ClaudeResponse(
        id="msg_1",
        model="claude-sonnet-4-5",
        content=[
            ClaudeContent(
                type="tool_result",
                tool_use_id="call_1",
                tool_result_content=[ClaudeContent(text="72F")],
            )
        ],
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    result = ir.tool_results[0]
    assert result.role == "tool"
    assert result.tool_call_id == "call_1"
    assert result.content == "72F"


@pytest.mark.parametrize(
    ("stop_reason", "canonical"),
    [
        ("end_turn", "stop"),
        ("max_tokens", "length"),
        ("stop_sequence", "stop"),
        ("tool_use", "tool_calls"),
        (None, None),
    ],
)
def test_response_finish_reasons_normalized(
    ctx: ConversionContext, stop_reason: str | None, canonical: str | None
) -> None:
    """Claude stop reasons normalize through the shared policy."""
    response = ClaudeResponse(
        id="msg_1",
        model="claude-sonnet-4-5",
        content=[ClaudeContent(text="Hi")],
        stop_reason=stop_reason,
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason == canonical


def test_response_usage_cache_details(ctx: ConversionContext) -> None:
    """Usage cache fields map into RelayUsage."""
    response = ClaudeResponse(
        id="msg_1",
        model="claude-sonnet-4-5",
        content=[ClaudeContent(text="Hi")],
        usage=ClaudeUsage(
            input_tokens=10,
            output_tokens=5,
            cache_creation_input_tokens=4,
            cache_read_input_tokens=3,
        ),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.usage == RelayUsage(
        prompt_tokens=17,
        completion_tokens=5,
        cache_creation_tokens=4,
        cache_read_tokens=3,
        input_tokens=17,
    )


def test_response_stop_sequence_preserved(ctx: ConversionContext) -> None:
    """The matched stop sequence survives in canonical passthrough."""
    response = ClaudeResponse(
        id="msg_1",
        model="claude-sonnet-4-5",
        content=[ClaudeContent(text="Hi")],
        stop_reason="stop_sequence",
        stop_sequence="END",
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason == "stop"
    assert ir.passthrough["stop_sequence"] == "END"


def test_response_unknown_passthrough(ctx: ConversionContext) -> None:
    """Unknown response fields survive in canonical passthrough."""
    response = ClaudeResponse(
        id="msg_1",
        model="claude-sonnet-4-5",
        content=[ClaudeContent(text="Hi")],
        passthrough={"x_msg_id": "r"},
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.passthrough["x_msg_id"] == "r"


def test_response_wrong_type_returns_unsupported_format(ctx: ConversionContext) -> None:
    """A non-response payload is rejected as unsupported_format."""
    request = claude_req(messages=[claude_msg("user", [ClaudeContent(text="hi")])])
    result = mapper.response_to_ir(request, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value


# ---------------------------------------------------------------------------
# ir_to_response
# ---------------------------------------------------------------------------


def test_ir_to_response_builds_valid_response(ctx: ConversionContext) -> None:
    """Canonical response maps to a valid Claude Messages response."""
    ir = RelayResponse(
        model="claude-sonnet-4-5",
        id="msg_1",
        content="Hi",
        finish_reason="stop",
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert isinstance(response, ClaudeResponse)
    assert response.id == "msg_1"
    assert response.type == "message"
    assert response.role == "assistant"
    assert response.model == "claude-sonnet-4-5"
    assert response.content[0].type == "text"
    assert response.content[0].text == "Hi"
    assert response.stop_reason == "end_turn"
    assert response.stop_sequence is None


def test_ir_to_response_thinking_signature_emitted(ctx: ConversionContext) -> None:
    """Thinking content is not emitted as a wire thinking block."""
    ir = RelayResponse(
        model="claude-sonnet-4-5",
        content="Hi",
        thinking=ThinkingResult(content="think", signature="sig123"),
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert len(response.content) == 1
    assert response.content[0].type == "text"
    assert response.content[0].text == "Hi"


def test_ir_to_response_tool_use_blocks(ctx: ConversionContext) -> None:
    """Tool calls map to Claude tool_use blocks with native input dicts."""
    ir = RelayResponse(
        model="claude-sonnet-4-5",
        tool_calls=[
            ToolCall(
                id="call_1",
                type="custom",
                function=FunctionCall(name="get_weather", arguments={"city": "SF"}),
            )
        ],
        finish_reason="tool_calls",
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    block = response.content[0]
    assert block.type == "tool_use"
    assert block.tool_use_id == "call_1"
    assert block.name == "get_weather"
    assert block.input == {"city": "SF"}
    assert response.stop_reason == "tool_use"


@pytest.mark.parametrize(
    ("canonical", "stop_reason"),
    [
        ("stop", "end_turn"),
        ("length", "max_tokens"),
        ("tool_calls", "tool_use"),
        (None, None),
    ],
)
def test_ir_to_response_finish_reasons(
    ctx: ConversionContext, canonical: str | None, stop_reason: str | None
) -> None:
    """Canonical finish reasons map back to Claude stop reasons."""
    ir = RelayResponse(model="claude-sonnet-4-5", content="Hi", finish_reason=canonical)
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.stop_reason == stop_reason


def test_ir_to_response_usage_reconstructed(ctx: ConversionContext) -> None:
    """RelayUsage reconstructs a ClaudeUsage with cache details."""
    ir = RelayResponse(
        model="claude-sonnet-4-5",
        content="Hi",
        usage=RelayUsage(
            prompt_tokens=10,
            completion_tokens=5,
            cache_creation_tokens=4,
            cache_read_tokens=3,
        ),
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.usage == ClaudeUsage(
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=4,
        cache_read_input_tokens=3,
    )


def test_ir_to_response_no_usage_when_none(ctx: ConversionContext) -> None:
    """None usage is omitted from the wire response."""
    ir = RelayResponse(model="claude-sonnet-4-5", content="Hi")
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.usage is None


def test_ir_to_response_stop_sequence_roundtrip(ctx: ConversionContext) -> None:
    """A preserved stop sequence restores a stop_sequence finish."""
    ir = RelayResponse(
        model="claude-sonnet-4-5",
        content="Hi",
        finish_reason="stop",
        passthrough={"stop_sequence": "END"},
    )
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.stop_reason == "stop_sequence"
    assert response.stop_sequence == "END"
    assert response.passthrough.get("stop_sequence") is None


def test_ir_to_response_defaults(ctx: ConversionContext) -> None:
    """Missing id defaults to a generated id without errors."""
    ir = RelayResponse(model="claude-sonnet-4-5")
    response = mapper.ir_to_response(ir, context=ctx).unwrap()
    assert response.id.startswith("chatcmpl-")
    assert response.content == []


def test_stream_ops_unsupported_until_shared_lifecycle(ctx: ConversionContext) -> None:
    """Stream conversion is deferred to the shared stream lifecycle task."""
    event = ClaudeResponse(id="msg_1", model="claude-sonnet-4-5")
    state = StreamState(
        source=RelayFormat.CLAUDE,
        target=RelayFormat.CLAUDE,
        model="claude-sonnet-4-5",
    )
    result = mapper.stream_to_delta(event, state=state)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FEATURE.value
