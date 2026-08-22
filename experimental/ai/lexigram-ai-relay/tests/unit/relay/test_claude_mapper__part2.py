
import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.claude import ClaudeMapper
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.relay.dto import (
    ClaudeContent,
    ClaudeResponse,
    ClaudeUsage,
)
from lexigram.contracts.ai.relay.ir import RelayRequest, RelayResponse, StreamState
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.ai.thinking import ThinkingConfig, ThinkingResult

mapper = ClaudeMapper()

from ._test_claude_mapper_support import (
    claude_msg,
    claude_req,
)


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
