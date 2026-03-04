"""Tests for the Gemini ``generateContent`` request/response mapper."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.base import FormatMapper
from lexigram.ai.relay.mappers.gemini import GeminiMapper
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageBase64Part, ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.context import GeminiOptions, RelayOptions
from lexigram.contracts.ai.relay.dto import (
    GeminiCandidate,
    GeminiContent,
    GeminiGroundingMetadata,
    GeminiPart,
    GeminiPromptFeedback,
    GeminiRequest,
    GeminiResponse,
    GeminiSafetyRating,
    GeminiUsageMetadata,
)
from lexigram.contracts.ai.relay.ir import RelayRequest, RelayResponse, StreamState
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.ai.thinking import ThinkingConfig, ThinkingResult
from lexigram.contracts.core.result import Ok

mapper = GeminiMapper()


def gemini_req(**kwargs: Any) -> GeminiRequest:
    """Build a Gemini request with sensible defaults."""
    defaults: dict[str, Any] = {"contents": []}
    defaults.update(kwargs)
    return GeminiRequest(**defaults)


def gemini_content(role: str, *parts: GeminiPart) -> GeminiContent:
    """Build a Gemini content turn."""
    return GeminiContent(role=role, parts=list(parts))


def gen_config(**kwargs: Any) -> dict[str, Any]:
    """Build a generationConfig dict."""
    return {k: v for k, v in kwargs.items() if v is not None}


def text_part(text: str) -> GeminiPart:
    """Build a text part."""
    return GeminiPart(text=text)


def thought_part(text: str, signature: str | None = None) -> GeminiPart:
    """Build a thought part."""
    return GeminiPart(text=text, thought=True, thought_signature=signature)


def inline_part(mime_type: str, data: str) -> GeminiPart:
    """Build an inlineData image part."""
    return GeminiPart(inline_data={"mimeType": mime_type, "data": data})


def function_call_part(name: str, args: dict[str, Any]) -> GeminiPart:
    """Build a functionCall part."""
    return GeminiPart(function_call={"name": name, "args": args})


def function_response_part(name: str, response: Any) -> GeminiPart:
    """Build a functionResponse part."""
    return GeminiPart(function_response={"name": name, "response": response})


class FakeResolver:
    """Structural media resolver returning a fixed base64 payload."""

    def resolve(self, url: str) -> object:
        return Ok(("image/png", "AAAB"))


@pytest.fixture
def ctx() -> ConversionContext:
    """A fresh conversion context per test."""
    return ConversionContext()


def test_mapper_implements_format_mapper_protocol() -> None:
    """The Gemini mapper satisfies the FormatMapper protocol."""
    assert isinstance(mapper, FormatMapper)
    assert mapper.format is RelayFormat.GEMINI


# ---------------------------------------------------------------------------
# request_to_ir
# ---------------------------------------------------------------------------


def test_request_wrong_type(ctx: ConversionContext) -> None:
    """A non-Gemini payload is an unsupported_format error."""
    from lexigram.contracts.ai.relay.dto import ClaudeRequest

    payload = ClaudeRequest(model="c", max_tokens=10, messages=[])
    result = mapper.request_to_ir(payload, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value


def test_request_system_instruction(ctx: ConversionContext) -> None:
    """systemInstruction text becomes canonical system."""
    request = gemini_req(
        contents=[gemini_content("user", text_part("Hi"))],
        system_instruction={"parts": [{"text": "You are helpful."}]},
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.system == "You are helpful."


def test_request_system_instruction_multiple_parts(ctx: ConversionContext) -> None:
    """Multiple systemInstruction parts join with newlines."""
    request = gemini_req(
        contents=[],
        system_instruction={"parts": [{"text": "A"}, {"text": "B"}]},
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.system == "A\nB"


def test_request_user_text(ctx: ConversionContext) -> None:
    """A single text user part becomes a plain string."""
    request = gemini_req(contents=[gemini_content("user", text_part("Hello"))])
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.messages[0].role == "user"
    assert ir.messages[0].content == "Hello"


def test_request_user_text_and_inline_image(ctx: ConversionContext) -> None:
    """Text and inlineData parts become canonical content parts."""
    request = gemini_req(
        contents=[
            gemini_content(
                "user",
                text_part("look"),
                inline_part("image/png", "AAAB"),
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    parts = ir.messages[0].content
    assert isinstance(parts, list)
    assert parts[0] == TextPart(text="look")
    assert parts[1] == ImageBase64Part(
        data="AAAB", media_type="image/png", detail="auto"
    )


def test_request_model_role_to_assistant(ctx: ConversionContext) -> None:
    """The model role maps to the assistant role."""
    request = gemini_req(contents=[gemini_content("model", text_part("Sure."))])
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.messages[0].role == "assistant"
    assert ir.messages[0].content == "Sure."


def test_request_function_call_to_tool_call(ctx: ConversionContext) -> None:
    """A functionCall part becomes a canonical ToolCall."""
    request = gemini_req(
        contents=[
            gemini_content("model", function_call_part("get_weather", {"city": "SF"}))
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    tool_call = ir.messages[0].tool_calls[0]
    assert tool_call.id == ""
    assert tool_call.type == "custom"
    assert tool_call.function.name == "get_weather"
    assert tool_call.function.arguments == {"city": "SF"}


def test_request_function_role_to_tool(ctx: ConversionContext) -> None:
    """A function role with functionResponse becomes a canonical tool message."""
    request = gemini_req(
        contents=[
            gemini_content(
                "function", function_response_part("get_weather", {"temp": 72})
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    tool = ir.messages[0]
    assert tool.role == "tool"
    assert tool.tool_call_id == ""
    assert tool.content == '{"temp":72}'


def test_request_thought_parts(ctx: ConversionContext) -> None:
    """Thought parts map into assistant thinking blocks with signatures."""
    request = gemini_req(
        contents=[
            gemini_content(
                "model",
                thought_part("Hmm.", "sig123"),
                text_part("Answer."),
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    message = ir.messages[0]
    assert message.content == "Answer."
    blocks = message.thinking_blocks or []
    assert blocks[0] == {"thought": True, "text": "Hmm.", "thoughtSignature": "sig123"}


def test_request_generation_config(ctx: ConversionContext) -> None:
    """Generation config maps to canonical request fields."""
    request = gemini_req(
        contents=[gemini_content("user", text_part("hi"))],
        generation_config=gen_config(
            temperature=0.7,
            topP=0.9,
            topK=40,
            maxOutputTokens=512,
            stopSequences=["END"],
        ),
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.temperature == 0.7
    assert ir.top_p == 0.9
    assert ir.top_k == 40
    assert ir.max_tokens == 512
    assert ir.stop_sequences == ["END"]


def test_request_generation_config_zero_values(ctx: ConversionContext) -> None:
    """Explicit zero temperature survives into canonical IR."""
    request = gemini_req(
        contents=[gemini_content("user", text_part("hi"))],
        generation_config=gen_config(temperature=0.0, topP=0.0, topK=0),
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.temperature == 0.0
    assert ir.top_p == 0.0
    assert ir.top_k == 0


def test_request_response_mime_type_json(ctx: ConversionContext) -> None:
    """A JSON response mime type becomes a json_object response_format."""
    request = gemini_req(
        contents=[gemini_content("user", text_part("hi"))],
        generation_config=gen_config(responseMimeType="application/json"),
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.response_format == {"type": "json_object"}


def test_request_tools_to_definitions(ctx: ConversionContext) -> None:
    """functionDeclarations map to canonical ToolDefinition objects."""
    request = gemini_req(
        contents=[gemini_content("user", text_part("hi"))],
        tools=[
            {
                "functionDeclarations": [
                    {"name": "w", "description": "t", "parameters": {"type": "object"}}
                ]
            }
        ],
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.tools == [
        ToolDefinition(name="w", description="t", parameters={"type": "object"})
    ]


def test_request_tool_config_metadata(ctx: ConversionContext) -> None:
    """toolConfig is preserved as protocol metadata."""
    request = gemini_req(
        contents=[gemini_content("user", text_part("hi"))],
        tool_config={"functionCallingConfig": {"mode": "ANY"}},
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.metadata["tool_config"] == {"functionCallingConfig": {"mode": "ANY"}}


def test_request_safety_settings_metadata(ctx: ConversionContext) -> None:
    """Wire safety settings are preserved as protocol metadata."""
    settings = [
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"}
    ]
    request = gemini_req(
        contents=[gemini_content("user", text_part("hi"))],
        safety_settings=settings,
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.metadata["safety_settings"] == settings


def test_request_passthrough_fields(ctx: ConversionContext) -> None:
    """Unknown request fields survive in passthrough."""
    request = GeminiRequest(contents=[], passthrough={"custom": "value"})
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.passthrough["custom"] == "value"


def test_request_unknown_part_dropped(ctx: ConversionContext) -> None:
    """An unknown part type records a loss rather than failing."""
    request = gemini_req(
        contents=[
            GeminiContent(role="user", parts=[GeminiPart(passthrough={"video": True})])
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert len(ir.messages) == 0
    assert ctx.losses


# ---------------------------------------------------------------------------
# ir_to_request
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# response_to_ir
# ---------------------------------------------------------------------------


def test_response_wrong_type(ctx: ConversionContext) -> None:
    """A non-Gemini payload is an unsupported_format error."""
    from lexigram.contracts.ai.relay.dto import ClaudeResponse

    result = mapper.response_to_ir(ClaudeResponse(id="m", model="c"), context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value


def test_response_text(ctx: ConversionContext) -> None:
    """Candidate text maps to canonical content."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(content=gemini_content("model", text_part("Hi there")))
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == "Hi there"


def test_response_thinking_and_signature(ctx: ConversionContext) -> None:
    """Thought parts map into a ThinkingResult with signature and tokens."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(
                content=gemini_content("model", thought_part("Think.", "sig1"))
            )
        ],
        usage_metadata=GeminiUsageMetadata(
            prompt_token_count=10,
            candidates_token_count=5,
            total_token_count=15,
            thoughts_token_count=3,
        ),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.thinking is not None
    assert ir.thinking.content == "Think."
    assert ir.thinking.signature == "sig1"
    assert ir.thinking.tokens == 3


def test_response_function_call(ctx: ConversionContext) -> None:
    """A functionCall part maps to a canonical ToolCall."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(
                content=gemini_content("model", function_call_part("w", {"q": 1}))
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == ""
    assert ir.tool_calls[0].function.name == "w"
    assert ir.tool_calls[0].function.arguments == {"q": 1}


def test_response_tool_only_output(ctx: ConversionContext) -> None:
    """Tool-only output keeps content empty with tool calls populated."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(
                content=gemini_content("model", function_call_part("w", {})),
                finish_reason="STOP",
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == ""
    assert ir.tool_calls
    assert ir.finish_reason == "stop"


@pytest.mark.parametrize(
    ("wire", "expected"),
    [
        ("STOP", "stop"),
        ("MAX_TOKENS", "length"),
        ("SAFETY", "content_filter"),
        ("RECITATION", "content_filter"),
        ("MALFORMED_FUNCTION_CALL", "function_call"),
        ("OTHER", "other"),
        ("MODEL_FINISH_REASON_UNSPECIFIED", "other"),
        (None, None),
    ],
)
def test_response_finish_reasons(
    ctx: ConversionContext, wire: str | None, expected: str | None
) -> None:
    """Gemini finish reasons map to the canonical set."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(
                content=gemini_content("model", text_part("x")),
                finish_reason=wire,
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason == expected


def test_response_multiple_candidates_collapsed(ctx: ConversionContext) -> None:
    """Extra candidates collapse into the first with a loss."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(content=gemini_content("model", text_part("first"))),
            GeminiCandidate(content=gemini_content("model", text_part("second"))),
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == "first"
    assert any(loss.reason == "multiple_candidates_collapsed" for loss in ctx.losses)


def test_response_usage_metadata(ctx: ConversionContext) -> None:
    """usageMetadata maps into RelayUsage including cached and thoughts."""
    response = GeminiResponse(
        candidates=[GeminiCandidate(content=gemini_content("model", text_part("x")))],
        usage_metadata=GeminiUsageMetadata(
            prompt_token_count=100,
            candidates_token_count=20,
            total_token_count=120,
            cached_content_token_count=30,
            thoughts_token_count=5,
        ),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.usage == RelayUsage(
        prompt_tokens=100,
        completion_tokens=25,
        cache_read_tokens=30,
        reasoning_tokens=5,
        total_tokens_override=120,
    )


def test_response_model_version_passthrough(ctx: ConversionContext) -> None:
    """modelVersion and responseId survive as passthrough/metadata."""
    response = GeminiResponse(
        candidates=[GeminiCandidate(content=gemini_content("model", text_part("x")))],
        model_version="gemini-2.5-flash-001",
        response_id="resp_1",
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.id == "resp_1"
    assert ir.passthrough["model_version"] == "gemini-2.5-flash-001"


def test_response_prompt_feedback_passthrough(ctx: ConversionContext) -> None:
    """Prompt feedback survives as passthrough."""
    response = GeminiResponse(
        candidates=[GeminiCandidate(content=gemini_content("model", text_part("x")))],
        prompt_feedback=GeminiPromptFeedback(block_reason="SAFETY"),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.passthrough["prompt_feedback"] == {"blockReason": "SAFETY"}


def test_response_safety_and_grounding_passthrough(ctx: ConversionContext) -> None:
    """Candidate safety ratings and grounding metadata survive."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(
                content=gemini_content("model", text_part("x")),
                safety_ratings=[
                    GeminiSafetyRating(
                        category="HARM_CATEGORY_HATE_SPEECH", probability="HIGH"
                    )
                ],
                grounding_metadata=GeminiGroundingMetadata(web_search_queries=["q"]),
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.passthrough["safety_ratings"] == [
        {"category": "HARM_CATEGORY_HATE_SPEECH", "probability": "HIGH"}
    ]
    assert ir.passthrough["grounding_metadata"] == {"webSearchQueries": ["q"]}


def test_response_empty(ctx: ConversionContext) -> None:
    """An empty response yields defaults."""
    response = GeminiResponse()
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == ""
    assert ir.finish_reason is None
    assert ir.usage is None


# ---------------------------------------------------------------------------
# ir_to_response
# ---------------------------------------------------------------------------


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
