"""Tests for the OpenAI Responses request/response mapper."""

from __future__ import annotations

from lexigram.ai.relay.context import ConversionContext
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageBase64Part, ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import ResponsesItem, ResponsesRequest
from lexigram.contracts.ai.relay.ir import RelayRequest
from lexigram.contracts.ai.thinking import ThinkingConfig

def test_ir_to_request_system(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """System text maps to instructions."""
    request = RelayRequest(model="gpt-5.2", messages=[], system="Be concise.")
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert isinstance(wire, ResponsesRequest)
    assert wire.model == "gpt-5.2"
    assert wire.instructions == "Be concise."
    assert wire.input == []

def test_ir_to_request_text_message(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """A plain text message emits raw string content without a type."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[ChatMessage(role="user", content="hi")],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.input == [
        ResponsesItem(
            role="user",
            content="hi",
        )
    ]

def test_ir_to_request_multi_part_message(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Multimodal content emits input_image parts."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[
            ChatMessage(
                role="user",
                content=[
                    TextPart(text="look"),
                    ImageUrlPart(url="https://x/p.png", detail="low"),
                ],
            )
        ],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    item = wire.input[0]
    assert item.role == "user"
    assert item.content == [
        {"type": "input_text", "text": "look"},
        {"type": "input_image", "image_url": "https://x/p.png"},
    ]

def test_ir_to_request_base64_image(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Base64 images emit a data-URL input_image part."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[
            ChatMessage(
                role="user",
                content=[ImageBase64Part(data="AAAB", media_type="image/png")],
            )
        ],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.input[0].content == [
        {"type": "input_image", "image_url": "data:image/png;base64,AAAB"}
    ]

def test_ir_to_request_input_files_restored(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Metadata input_file parts are restored verbatim."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[
            ChatMessage(
                role="user",
                content="read",
                metadata={
                    "input_files": [
                        {
                            "type": "input_file",
                            "filename": "doc.pdf",
                            "file_data": {"file_id": "file_1"},
                        }
                    ]
                },
            )
        ],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.input[0].content == [
        {"type": "input_text", "text": "read"},
        {
            "type": "input_file",
            "filename": "doc.pdf",
            "file_data": {"file_id": "file_1"},
        },
    ]

def test_ir_to_request_item_id_restored(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Per-message item ids are restored on the wire item."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[
            ChatMessage(role="user", content="hi", metadata={"item_id": "msg_9"})
        ],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.input[0].id == "msg_9"

def test_ir_to_request_tool_message(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Tool messages emit function_call_output items."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[
            ChatMessage(
                role="tool",
                content="72F",
                tool_call_id="call_1",
                metadata={"item_id": "fcoc_1"},
            )
        ],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    item = wire.input[0]
    assert item.type == "function_call_output"
    assert item.call_id == "call_1"
    assert item.output == "72F"
    assert item.id == "fcoc_1"

def test_ir_to_request_tool_calls(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Assistant tool calls emit a message item plus function_call items."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[
            ChatMessage(
                role="assistant",
                content="Let me check.",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        type="function",
                        function=FunctionCall(
                            name="get_weather", arguments={"city": "SF"}
                        ),
                    )
                ],
                metadata={"function_call_item_ids": ["fc_1"]},
            )
        ],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert [i.type for i in wire.input] == [None, "function_call"]
    assert wire.input[0].content == "Let me check."
    call = wire.input[1]
    assert call.id == "fc_1"
    assert call.call_id == "call_1"
    assert call.name == "get_weather"
    assert call.arguments == '{"city":"SF"}'

def test_ir_to_request_tool_call_skips_empty_message(
    ctx: ConversionContext,
*, mapper: OpenAIResponsesMapper) -> None:
    """A tool-only assistant turn still emits the empty message item."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        function=FunctionCall(name="get_time", arguments="{}"),
                    )
                ],
            )
        ],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert [i.type for i in wire.input] == [None, "function_call"]

def test_ir_to_request_thinking_blocks(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Assistant thinking blocks do not emit a reasoning item."""
    summary = [{"type": "summary_text", "text": "Analyzing..."}]
    request = RelayRequest(
        model="gpt-5.2",
        messages=[
            ChatMessage(
                role="assistant",
                content="",
                thinking_blocks=summary,
                metadata={"item_id": "rs_1"},
            )
        ],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert len(wire.input) == 1
    assert wire.input[0].role == "assistant"
    assert wire.input[0].type is None

def test_ir_to_request_thinking_effort(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Thinking effort maps to the reasoning config."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[],
        thinking=ThinkingConfig(effort="medium"),
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.reasoning == {"effort": "medium"}

def test_ir_to_request_reasoning_metadata(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Metadata reasoning passthrough is restored."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[],
        metadata={"reasoning": {"effort": "low", "summary": "auto"}},
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.reasoning == {"effort": "low", "summary": "auto"}

def test_ir_to_request_include_usage(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """include_usage appends usage to include."""
    request = RelayRequest(model="gpt-5.2", messages=[], include_usage=True)
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.include == ["usage"]

def test_ir_to_request_include_metadata(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Requested include fields are restored alongside usage."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[],
        include_usage=True,
        metadata={"include": ["citations"]},
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.include == ["citations", "usage"]

def test_ir_to_request_response_format(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """A JSON schema response format maps to text.format."""
    schema = {"type": "object"}
    request = RelayRequest(
        model="gpt-5.2",
        messages=[],
        response_format={"type": "json_schema", "name": "weather", "schema": schema},
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.text == {
        "format": {"type": "json_schema", "name": "weather", "schema": schema}
    }

def test_ir_to_request_text_metadata_preserved(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Metadata text config is echoed when no response format exists."""
    text = {"format": {"type": "text"}}
    request = RelayRequest(model="gpt-5.2", messages=[], metadata={"text": text})
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.text == text

def test_ir_to_request_scalars(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Canonical scalars map back to wire fields."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[],
        temperature=0.5,
        max_tokens=100,
        stream=True,
        parallel_tool_calls=True,
        tools=[
            ToolDefinition(
                name="get_weather",
                description="Weather lookup",
                parameters={"type": "object"},
            )
        ],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.temperature == 0.5
    assert wire.max_output_tokens == 100
    assert wire.stream is True
    assert wire.parallel_tool_calls is True
    assert wire.tools == [
        {
            "type": "function",
            "name": "get_weather",
            "description": "Weather lookup",
            "parameters": {"type": "object"},
        }
    ]

def test_ir_to_request_service_tier_and_passthrough(
    ctx: ConversionContext,
*, mapper: OpenAIResponsesMapper) -> None:
    """service_tier and passthrough fields are restored."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[],
        metadata={"service_tier": "default"},
        passthrough={"seed": 7},
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.service_tier == "default"
    assert wire.passthrough == {"seed": 7}

def test_ir_to_request_web_search_restored(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Preserved web_search_call items restore as wire items."""
    search = {
        "type": "web_search_call",
        "id": "ws_1",
        "status": "searching",
    }
    request = RelayRequest(
        model="gpt-5.2",
        messages=[],
        metadata={"input_web_search_calls": [search]},
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    item = wire.input[0]
    assert item.type == "web_search_call"
    assert item.id == "ws_1"
    assert item.passthrough == {"status": "searching"}

def test_ir_to_request_system_message_folds(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """System-role messages fold into instructions with a loss."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[ChatMessage(role="system", content="Rule.")],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.instructions == "Rule."
    assert wire.input == []
    assert any(loss.reason == "system_message_reordered" for loss in ctx.losses)
