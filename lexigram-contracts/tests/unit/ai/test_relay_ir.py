"""Tests for the relay conversion IR and shared types (G-XX relay plan)."""
from __future__ import annotations

from lexigram.contracts.ai.relay import (
    PassthroughData,
    RelayConfig,
    RelayProtocol,
    RelayRequest,
    RelayResponse,
    RelayUsage,
    StreamMode,
)
from lexigram.contracts.ai.relay.ir import RelayError


def test_protocol_enum_values():
    """RelayProtocol maps to the four supported wire protocols."""
    assert RelayProtocol.OPENAI_CHAT.value == "openai_chat"
    assert RelayProtocol.CLAUDE.value == "claude"
    assert RelayProtocol.GEMINI.value == "gemini"
    assert RelayProtocol.RESPONSES.value == "responses"


def test_stream_mode_enum_values():
    """StreamMode only supports non-stream and SSE streaming."""
    assert StreamMode.NON_STREAM.value == "non_stream"
    assert StreamMode.STREAM_SSE.value == "stream_sse"


def test_relay_config_defaults():
    """RelayConfig defaults to non-streaming without passthrough."""
    config = RelayConfig()
    assert config.stream_mode is StreamMode.NON_STREAM
    assert config.passthrough is False


def test_relay_usage_defaults():
    """RelayUsage defaults to zero tokens and optional breakdown fields."""
    usage = RelayUsage()
    assert usage.prompt_tokens == 0
    assert usage.completion_tokens == 0
    assert usage.total_tokens == 0
    assert usage.cached_tokens is None
    assert usage.reasoning_tokens is None


def test_relay_request_build():
    """RelayRequest carries model, messages, tools, and parameters."""
    from lexigram.contracts.ai.agents import ToolDefinition
    from lexigram.contracts.ai.llm import ChatMessage

    request = RelayRequest(
        model="gpt-4o",
        messages=[ChatMessage(role="user", content="hi")],
        tools=[ToolDefinition(name="add", description="Adds", parameters={})],
        parameters={"temperature": 0.5},
        stream=True,
    )
    assert request.model == "gpt-4o"
    assert request.stream is True
    assert request.parameters["temperature"] == 0.5
    assert request.tools is not None
    assert request.tools[0].name == "add"
    assert request.messages[0].content == "hi"


def test_relay_request_passthrough_and_metadata():
    """RelayRequest keeps protocol-specific extras in passthrough dicts."""
    request = RelayRequest(
        model="claude-3-5-sonnet",
        messages=[],
        passthrough={"thinking": {"type": "enabled"}},
        metadata={"channel_id": 1},
    )
    assert request.passthrough["thinking"]["type"] == "enabled"
    assert request.metadata["channel_id"] == 1


def test_relay_response_build():
    """RelayResponse carries content, thinking, tool calls, and usage."""
    from lexigram.contracts.ai.llm import FunctionCall, ToolCall
    from lexigram.contracts.ai.thinking import ThinkingResult

    response = RelayResponse(
        model="gemini-2.0-flash",
        content="42",
        thinking=ThinkingResult(content="let me think"),
        tool_calls=[ToolCall(id="call_1", function=FunctionCall(name="add", arguments='{"a":1,"b":2}'))],
        finish_reason="tool_calls",
        usage=RelayUsage(prompt_tokens=10, completion_tokens=2, total_tokens=12),
    )
    assert response.content == "42"
    assert response.thinking is not None
    assert response.thinking.content == "let me think"
    assert response.tool_calls is not None
    assert response.tool_calls[0].id == "call_1"
    assert response.finish_reason == "tool_calls"
    assert response.usage is not None
    assert response.usage.total_tokens == 12


def test_relay_error_is_ai_error():
    """RelayError subclasses AIError and carries the LEX_ERR_AI code."""
    from lexigram.contracts.ai.exceptions import AIError

    error = RelayError("cannot convert")
    assert isinstance(error, AIError)
    assert error._code == "LEX_ERR_AI_003"
    assert "cannot convert" in str(error)


def test_passthrough_alias():
    """PassthroughData is a plain dict alias for protocol extras."""
    data: PassthroughData = {"tool_choice": "auto"}
    assert data["tool_choice"] == "auto"
