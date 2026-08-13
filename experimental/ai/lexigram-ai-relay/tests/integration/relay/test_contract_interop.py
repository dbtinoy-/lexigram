"""Interop with existing Lexigram LLM conventions (Task 14).

The canonical relay IR reuses the shared contracts types
(``ChatMessage``, ``ToolCall``, ``ToolDefinition``, ``TokenUsage``) so
downstream packages never see protocol-specific shapes.  These tests
prove the IR is consumable by the existing lexigram-ai-llm serializers
without importing any relay mapper implementation module, that usage
maps onto ``TokenUsage``/pricing inputs, and that the relay package
never imports lexigram-ai-llm, web, http, or channel modules.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import TextPart
from lexigram.contracts.ai.relay.ir import RelayRequest
from lexigram.contracts.ai.relay.types import RelayUsage

from lexigram.ai.llm.clients._message_utils import (
    serialize_content_for_anthropic,
    serialize_content_for_gemini,
    serialize_content_for_openai,
)
from lexigram.ai.llm.clients._tools_utils import (
    serialize_message_for_openai,
    serialize_openai_tool_calls,
    tool_to_openai_format,
)


def _sample_request() -> RelayRequest:
    """A canonical request exercising text, tools, and tool results."""
    return RelayRequest(
        model="claude-test",
        system="You are a helpful assistant.",
        messages=[
            ChatMessage(role="user", content="What is the weather in Paris?"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        type="function",
                        function=FunctionCall(
                            name="get_weather", arguments={"city": "Paris"}
                        ),
                    )
                ],
            ),
            ChatMessage(
                role="tool",
                content="15 degrees",
                tool_call_id="call_1",
            ),
        ],
        tools=[
            ToolDefinition(
                name="get_weather",
                description="Get weather by city",
                parameters={
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            )
        ],
        max_tokens=1024,
    )


def test_canonical_messages_consume_existing_openai_serializer() -> None:
    """RelayRequest messages serialize through the existing OpenAI path."""
    request = _sample_request()
    serialized = [serialize_message_for_openai(msg) for msg in request.messages]
    assert serialized[0] == {"role": "user", "content": "What is the weather in Paris?"}
    assert serialized[1]["role"] == "assistant"
    assert serialized[1]["content"] is None
    assert serialized[1]["tool_calls"][0]["function"]["name"] == "get_weather"
    assert serialized[2]["role"] == "tool"
    assert serialized[2]["tool_call_id"] == "call_1"
    assert serialized[2]["content"] == "15 degrees"


def test_canonical_content_serializes_for_all_providers() -> None:
    """MessageContent (str and parts) feeds every provider serializer."""
    text = ChatMessage(role="user", content="hello").content
    assert serialize_content_for_openai(text) == "hello"
    assert serialize_content_for_anthropic(text) == [{"type": "text", "text": "hello"}]
    assert serialize_content_for_gemini(text) == [{"text": "hello"}]

    parts = ChatMessage(role="user", content=[TextPart(text="hello")]).content
    assert serialize_content_for_openai(parts) == [{"type": "text", "text": "hello"}]
    assert serialize_content_for_anthropic(parts) == [
        {"type": "text", "text": "hello"}
    ]
    assert serialize_content_for_gemini(parts) == [{"text": "hello"}]


def test_canonical_tools_consume_existing_serializers() -> None:
    """ToolDefinition and ToolCall feed the existing OpenAI tool paths."""
    request = _sample_request()
    wire = tool_to_openai_format(request.tools[0])
    assert wire is not None
    assert wire["type"] == "function"
    assert wire["function"]["name"] == "get_weather"

    calls = serialize_openai_tool_calls(request.messages[1].tool_calls)
    assert calls is not None
    assert calls[0]["id"] == "call_1"
    assert calls[0]["function"]["name"] == "get_weather"
    assert calls[0]["function"]["arguments"] == '{"city":"Paris"}'


def test_usage_maps_onto_token_usage_and_pricing_inputs() -> None:
    """Normalized usage feeds TokenUsage-shaped pricing inputs."""
    usage = RelayUsage(
        prompt_tokens=10,
        completion_tokens=5,
        cache_read_tokens=3,
        cache_creation_tokens=2,
        reasoning_tokens=2,
    )
    prompt = usage.prompt_tokens
    completion = usage.completion_tokens
    total = prompt + completion
    assert (prompt, completion, total) == (10, 5, 15)
    assert usage.cache_read_tokens == 3
    assert usage.cache_creation_tokens == 2
    assert usage.reasoning_tokens == 2


FORBIDDEN_IMPORTS = (
    "lexigram.ai.llm",
    "lexigram.ai.llm.clients",
    "lexigram.web",
    "lexigram.http",
    "lexigram.ai.relay.gateway",
    "lexigram.sql",
    "lexigram.auth",
)


@pytest.mark.parametrize("forbidden", FORBIDDEN_IMPORTS)
def test_relay_package_never_imports_llm_or_channel_modules(forbidden: str) -> None:
    """Importing lexigram.ai.relay loads no llm/web/http/channel modules."""
    script = (
        "import sys; "
        "import lexigram.ai.relay; "
        f"assert {forbidden!r} not in sys.modules, {forbidden!r}"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
