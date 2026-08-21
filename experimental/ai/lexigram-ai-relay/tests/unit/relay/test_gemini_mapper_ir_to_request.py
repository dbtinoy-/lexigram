"""Gemini mapper tests: canonical IR to wire request (``ir_to_request``)."""

from __future__ import annotations

from gemini_mapper_test_helpers import FakeResolver, mapper
from lexigram.ai.relay.context import ConversionContext
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageBase64Part, ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.context import GeminiOptions, RelayOptions
from lexigram.contracts.ai.relay.dto import GeminiRequest
from lexigram.contracts.ai.relay.ir import RelayRequest
from lexigram.contracts.ai.thinking import ThinkingConfig


def test_ir_to_request_system(ctx: ConversionContext) -> None:
    """Canonical system becomes a Gemini systemInstruction."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        system="Be nice",
        messages=[ChatMessage(role="user", content="Hello")],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert isinstance(request, GeminiRequest)
    assert request.system_instruction == {"parts": [{"text": "Be nice"}]}
    assert request.contents[0].role == "user"
    assert request.contents[0].parts[0].text == "Hello"


def test_ir_to_request_system_folded_from_messages(ctx: ConversionContext) -> None:
    """System role messages fold into the Gemini systemInstruction."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[
            ChatMessage(role="system", content="System text"),
            ChatMessage(role="user", content="Hello"),
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.system_instruction == {"parts": [{"text": "System text"}]}
    assert request.contents[0].role == "user"


def test_ir_to_request_user_multimodal(ctx: ConversionContext) -> None:
    """Canonical base64 image parts map to inlineData parts."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
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
    parts = request.contents[0].parts
    assert parts[0].text == "see"
    assert parts[1].inline_data == {"mimeType": "image/png", "data": "AAAB"}


def test_ir_to_request_url_image_resolved(ctx: ConversionContext) -> None:
    """A media resolver converts a URL image into an inlineData part."""
    ctx = ConversionContext(media_resolver=FakeResolver())
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[
            ChatMessage(role="user", content=[ImageUrlPart(url="https://x/i.png")])
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.contents[0].parts[0].inline_data == {
        "mimeType": "image/png",
        "data": "AAAB",
    }


def test_ir_to_request_url_image_requires_resolver(ctx: ConversionContext) -> None:
    """URL images without a resolver are a media_resolution_required error."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[
            ChatMessage(role="user", content=[ImageUrlPart(url="https://x/i.png")])
        ],
    )
    result = mapper.ir_to_request(ir, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.MEDIA_RESOLUTION_REQUIRED.value


def test_ir_to_request_assistant_text_and_tool_call(ctx: ConversionContext) -> None:
    """Assistant content and tool calls map back to model parts."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[
            ChatMessage(
                role="assistant",
                content="Calling now.",
                tool_calls=[
                    ToolCall(
                        id="get_weather",
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
    parts = request.contents[0].parts
    assert request.contents[0].role == "model"
    assert parts[0].text == "Calling now."
    assert parts[1].function_call == {"name": "get_weather", "args": {"city": "SF"}}


def test_ir_to_request_assistant_thinking_blocks(ctx: ConversionContext) -> None:
    """Thinking blocks map back to thought parts with signatures preserved."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[
            ChatMessage(
                role="assistant",
                content="Answer.",
                thinking_blocks=[
                    {"thought": True, "text": "Hmm.", "thoughtSignature": "sig123"}
                ],
            )
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    parts = request.contents[0].parts
    assert parts[0].text == "Hmm."
    assert parts[0].thought is True
    assert parts[0].thought_signature == "sig123"


def test_ir_to_request_thinking_signature_bypassed() -> None:
    """The bypass policy drops signatures only when enabled and required."""
    options = RelayOptions(
        gemini=GeminiOptions(thought_signature_bypass=True),
    )
    ctx = ConversionContext(
        options=options,
        preserve_thinking_suffix=lambda model: model == "gemini-2.5-flash",
    )
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[
            ChatMessage(
                role="assistant",
                content="Answer.",
                thinking_blocks=[
                    {"thought": True, "text": "Hmm.", "thoughtSignature": "sig123"}
                ],
            )
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert (
        request.contents[0].parts[0].thought_signature
        == "context_engineering_is_the_way_to_go"
    )


def test_ir_to_request_thinking_signature_kept_without_bypass(
    ctx: ConversionContext,
) -> None:
    """Without the bypass option signatures stay intact."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[
            ChatMessage(
                role="assistant",
                content="Answer.",
                thinking_blocks=[
                    {"thought": True, "text": "Hmm.", "thoughtSignature": "sig123"}
                ],
            )
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.contents[0].parts[0].thought_signature == "sig123"


def test_ir_to_request_tool_message(ctx: ConversionContext) -> None:
    """Canonical tool messages become user-role function responses."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(
                        id="get_weather",
                        function=FunctionCall(
                            name="get_weather", arguments={"city": "SF"}
                        ),
                    )
                ],
            ),
            ChatMessage(
                role="tool",
                content='{"temp":72}',
                tool_call_id="get_weather",
            ),
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.contents[1].role == "user"
    assert request.contents[1].parts[0].function_response == {
        "name": "get_weather",
        "response": {"temp": 72},
    }


def test_ir_to_request_generation_config_roundtrip(ctx: ConversionContext) -> None:
    """Protocol generation config combines with canonical overrides."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[ChatMessage(role="user", content="hi")],
        temperature=0.2,
        metadata={"generation_config": {"temperature": 0.9, "candidateCount": 2}},
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    config = request.generation_config
    assert config["temperature"] == 0.2
    assert config["candidateCount"] == 2


def test_ir_to_request_stop_sequences(ctx: ConversionContext) -> None:
    """Canonical stop sequences become generationConfig stopSequences."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[ChatMessage(role="user", content="hi")],
        stop_sequences=["END"],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.generation_config["stopSequences"] == ["END"]


def test_ir_to_request_tools(ctx: ConversionContext) -> None:
    """Canonical tools become functionDeclarations."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[ChatMessage(role="user", content="hi")],
        tools=[
            ToolDefinition(
                name="w",
                description="t",
                parameters={"type": "object"},
            )
        ],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.tools == [
        {
            "functionDeclarations": [
                {"name": "w", "description": "t", "parameters": {"type": "OBJECT"}}
            ]
        }
    ]


def test_ir_to_request_tool_config(ctx: ConversionContext) -> None:
    """toolConfig comes back from protocol metadata."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[ChatMessage(role="user", content="hi")],
        metadata={"tool_config": {"functionCallingConfig": {"mode": "ANY"}}},
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.tool_config == {"functionCallingConfig": {"mode": "ANY"}}


def test_ir_to_request_safety_settings_preserved(ctx: ConversionContext) -> None:
    """Existing safety settings win over the callback."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[ChatMessage(role="user", content="hi")],
        metadata={
            "safety_settings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}
            ]
        },
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.safety_settings == [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}
    ]


def test_ir_to_request_safety_settings_from_callback() -> None:
    """The safety callback supplies thresholds only for non-empty results."""
    ctx = ConversionContext(
        safety_setting=lambda category: (
            "BLOCK_ONLY_HIGH" if category == "HARM_CATEGORY_HATE_SPEECH" else None
        )
    )
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[ChatMessage(role="user", content="hi")],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.safety_settings == [
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"}
    ]


def test_ir_to_request_no_safety_settings_default(ctx: ConversionContext) -> None:
    """With no callback the safety list stays None."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[ChatMessage(role="user", content="hi")],
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.safety_settings is None


def test_ir_to_request_thinking_budget(ctx: ConversionContext) -> None:
    """Canonical thinking budget is unsupported without the adapter."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[ChatMessage(role="user", content="hi")],
        thinking=ThinkingConfig(budget_tokens=1234),
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert "thinkingConfig" not in request.generation_config
    assert any(loss.reason == "thinking_not_supported" for loss in ctx.losses)


def test_ir_to_request_thinking_adapter() -> None:
    """The Gemini adapter injects a thinking budget when enabled."""
    options = RelayOptions(
        gemini=GeminiOptions(thinking_adapter_enabled=True, thinking_budget=2048)
    )
    ctx = ConversionContext(options=options)
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[ChatMessage(role="user", content="hi")],
        thinking=ThinkingConfig(budget_tokens=1000),
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.generation_config["thinkingConfig"] == {"thinkingBudget": 2048}


def test_ir_to_request_response_format_json(ctx: ConversionContext) -> None:
    """A json_object response format becomes a JSON mime type."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[ChatMessage(role="user", content="hi")],
        response_format={"type": "json_object"},
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert request.generation_config["responseMimeType"] == "application/json"


def test_ir_to_request_stream_passthrough(ctx: ConversionContext) -> None:
    """The stream flag is not carried on the Gemini wire payload."""
    ir = RelayRequest(
        model="gemini-2.5-flash",
        messages=[ChatMessage(role="user", content="hi")],
        stream=True,
    )
    request = mapper.ir_to_request(ir, context=ctx).unwrap()
    assert "stream" not in request.passthrough
