

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.base import FormatMapper
from lexigram.ai.relay.mappers.claude import ClaudeMapper
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageBase64Part, ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import (
    ClaudeContent,
    ClaudeRequest,
    ClaudeResponse,
)
from lexigram.contracts.ai.relay.ir import RelayRequest
from lexigram.contracts.ai.relay.types import RelayFormat
from lexigram.contracts.ai.thinking import ThinkingConfig

mapper = ClaudeMapper()

from ._test_claude_mapper_support import (
    FakeResolver,
    claude_msg,
    claude_req,
)


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
