"""Gemini mapper tests: wire request to canonical IR (``request_to_ir``)."""

from __future__ import annotations

from gemini_mapper_test_helpers import (
    function_call_part,
    function_response_part,
    gen_config,
    gemini_content,
    gemini_req,
    inline_part,
    mapper,
    text_part,
    thought_part,
)
from lexigram.ai.relay.context import ConversionContext
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.multimodal import ImageBase64Part, TextPart
from lexigram.contracts.ai.relay.dto import GeminiContent, GeminiPart, GeminiRequest


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
