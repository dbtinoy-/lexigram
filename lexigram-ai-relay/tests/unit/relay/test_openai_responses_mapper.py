"""Tests for the OpenAI Responses request/response mapper."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.mappers.base import FormatMapper
from lexigram.ai.relay.mappers.openai_responses import OpenAIResponsesMapper
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageBase64Part, ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import (
    ResponsesEvent,
    ResponsesIncompleteDetails,
    ResponsesItem,
    ResponsesRequest,
    ResponsesResponse,
    ResponsesUsage,
)
from lexigram.contracts.ai.relay.ir import RelayRequest, RelayResponse, StreamState
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.ai.thinking import ThinkingConfig, ThinkingResult

mapper = OpenAIResponsesMapper()


def resp_req(**kwargs: Any) -> ResponsesRequest:
    """Build a Responses request with sensible defaults."""
    defaults: dict[str, Any] = {"model": "gpt-5.2", "input": []}
    defaults.update(kwargs)
    return ResponsesRequest(**defaults)


def item(**kwargs: Any) -> ResponsesItem:
    """Build a Responses input item with sensible defaults."""
    defaults: dict[str, Any] = {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "hi"}],
    }
    defaults.update(kwargs)
    return ResponsesItem(**defaults)


def resp(**kwargs: Any) -> ResponsesResponse:
    """Build a Responses response with sensible defaults."""
    defaults: dict[str, Any] = {"id": "resp_1", "model": "gpt-5.2", "output": []}
    defaults.update(kwargs)
    return ResponsesResponse(**defaults)


def usage(**kwargs: Any) -> ResponsesUsage:
    """Build Responses usage with sensible defaults."""
    defaults: dict[str, Any] = {"input_tokens": 10, "output_tokens": 5}
    defaults.update(kwargs)
    return ResponsesUsage(**defaults)


@pytest.fixture
def ctx() -> ConversionContext:
    """A fresh conversion context per test."""
    return ConversionContext()


def test_mapper_implements_format_mapper_protocol() -> None:
    """The Responses mapper satisfies the FormatMapper protocol."""
    assert isinstance(mapper, FormatMapper)
    assert mapper.format is RelayFormat.OPENAI_RESPONSES


def test_wrong_request_type(ctx: ConversionContext) -> None:
    """Non-Responses payloads are rejected as unsupported format."""
    result = mapper.request_to_ir({"model": "x"}, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value


def test_wrong_response_type(ctx: ConversionContext) -> None:
    """Non-Responses payloads are rejected as unsupported format."""
    result = mapper.response_to_ir({"id": "x"}, context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value


# ---------------------------------------------------------------------------
# request_to_ir
# ---------------------------------------------------------------------------


def test_request_string_input(ctx: ConversionContext) -> None:
    """A plain string input becomes a single user message."""
    ir = mapper.request_to_ir(resp_req(input="Hello there"), context=ctx).unwrap()
    assert ir.model == "gpt-5.2"
    assert ir.messages == [ChatMessage(role="user", content="Hello there")]
    assert ir.system is None


def test_request_message_text_collapses(ctx: ConversionContext) -> None:
    """A single input_text part collapses to a plain string."""
    request = resp_req(
        input=[item(role="user", content=[{"type": "input_text", "text": "hi"}])]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.messages[0].role == "user"
    assert ir.messages[0].content == "hi"
    assert ir.messages[0].metadata is None


def test_request_message_item_id_preserved(ctx: ConversionContext) -> None:
    """The item id is preserved on message metadata."""
    request = resp_req(input=[item(id="msg_1")])
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.messages[0].metadata == {"item_id": "msg_1"}


def test_request_text_and_image_parts(ctx: ConversionContext) -> None:
    """input_text and input_image map to canonical content parts."""
    request = resp_req(
        input=[
            item(
                content=[
                    {"type": "input_text", "text": "what is in"},
                    {
                        "type": "input_image",
                        "image_url": {"url": "https://x/p.png", "detail": "high"},
                    },
                ]
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.messages[0].content == [
        TextPart(text="what is in"),
        ImageUrlPart(url="https://x/p.png", detail="high"),
    ]


def test_request_input_file_preserved(ctx: ConversionContext) -> None:
    """input_file parts are kept on metadata and recorded as a loss."""
    request = resp_req(
        input=[
            item(
                content=[
                    {"type": "input_text", "text": "read it"},
                    {
                        "type": "input_file",
                        "filename": "doc.pdf",
                        "file_data": {"file_id": "file_1"},
                    },
                ]
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    message = ir.messages[0]
    assert message.content == "read it"
    assert message.metadata == {
        "input_files": [
            {
                "type": "input_file",
                "filename": "doc.pdf",
                "file_data": {"file_id": "file_1"},
            }
        ]
    }
    assert any(loss.reason == "unrepresentable_part_preserved" for loss in ctx.losses)


def test_request_system_message_folds(ctx: ConversionContext) -> None:
    """A system-role message folds into the canonical system field."""
    request = resp_req(
        input=[
            item(
                role="system",
                content=[{"type": "input_text", "text": "Be concise."}],
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.system == "Be concise."
    assert ir.messages == []


def test_request_system_message_reordered_loss(ctx: ConversionContext) -> None:
    """A trailing system message records a reorder loss."""
    request = resp_req(
        input=[
            item(),
            item(
                role="system",
                content=[{"type": "input_text", "text": "Later rule."}],
            ),
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.system == "Later rule."
    assert len(ir.messages) == 1
    assert any(loss.reason == "system_message_reordered" for loss in ctx.losses)


def test_request_instructions(ctx: ConversionContext) -> None:
    """Instructions map to the canonical system field."""
    ir = mapper.request_to_ir(
        resp_req(instructions="You are helpful.", input="hi"), context=ctx
    ).unwrap()
    assert ir.system == "You are helpful."


def test_request_function_call_item(ctx: ConversionContext) -> None:
    """function_call items become canonical tool calls on an assistant turn."""
    request = resp_req(
        input=[
            item(),
            item(
                type="function_call",
                id="fc_1",
                call_id="call_1",
                name="get_weather",
                arguments='{"city": "SF"}',
            ),
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assistant = ir.messages[1]
    assert assistant.role == "assistant"
    assert assistant.content == ""
    assert assistant.tool_calls == [
        ToolCall(
            id="call_1",
            type="function",
            function=FunctionCall(name="get_weather", arguments={"city": "SF"}),
        )
    ]
    assert assistant.metadata == {"function_call_item_ids": ["fc_1"]}


def test_request_consecutive_function_calls_grouped(
    ctx: ConversionContext,
) -> None:
    """Consecutive function_call items merge into one assistant turn."""
    request = resp_req(
        input=[
            item(
                type="function_call",
                call_id="call_1",
                name="get_weather",
                arguments="{}",
            ),
            item(
                type="function_call",
                call_id="call_2",
                name="get_time",
                arguments="{}",
            ),
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert len(ir.messages) == 1
    assert [call.id for call in ir.messages[0].tool_calls] == ["call_1", "call_2"]


def test_request_function_call_keeps_invalid_arguments(
    ctx: ConversionContext,
) -> None:
    """Unparseable argument JSON is preserved verbatim."""
    request = resp_req(
        input=[
            item(
                type="function_call",
                call_id="call_1",
                name="get_weather",
                arguments='{"city":',
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    function = ir.messages[0].tool_calls[0].function
    assert isinstance(function, FunctionCall)
    assert function.arguments == '{"city":'


def test_request_function_call_output(ctx: ConversionContext) -> None:
    """function_call_output items become canonical tool messages."""
    request = resp_req(
        input=[
            item(
                type="function_call_output",
                id="fcoc_1",
                call_id="call_1",
                output="72F",
            )
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    message = ir.messages[0]
    assert message.role == "tool"
    assert message.tool_call_id == "call_1"
    assert message.content == "72F"
    assert message.metadata == {"item_id": "fcoc_1"}


def test_request_tool_turn_order(ctx: ConversionContext) -> None:
    """User, function call, then output preserve message order."""
    request = resp_req(
        input=[
            item(),
            item(
                type="function_call",
                call_id="call_1",
                name="get_weather",
                arguments="{}",
            ),
            item(type="function_call_output", call_id="call_1", output="72F"),
            item(content=[{"type": "input_text", "text": "thanks"}]),
        ]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert [message.role for message in ir.messages] == [
        "user",
        "assistant",
        "tool",
        "user",
    ]
    assert ir.messages[3].content == "thanks"


def test_request_reasoning_item(ctx: ConversionContext) -> None:
    """Reasoning summaries are preserved as raw thinking blocks."""
    summary = [{"type": "summary_text", "text": "Step by step..."}]
    request = resp_req(input=[item(type="reasoning", id="rs_1", summary=summary)])
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    message = ir.messages[0]
    assert message.role == "assistant"
    assert message.content == ""
    assert message.thinking_blocks == summary
    assert message.metadata == {"item_id": "rs_1"}


def test_request_web_search_call_preserved(ctx: ConversionContext) -> None:
    """web_search_call items are preserved on request metadata."""
    search = {
        "type": "web_search_call",
        "id": "ws_1",
        "status": "searching",
    }
    request = resp_req(input=[ResponsesItem.from_dict(dict(search))])
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.metadata["input_web_search_calls"] == [search]
    assert any(loss.reason == "unsupported_item_preserved" for loss in ctx.losses)


def test_request_unknown_item_dropped(ctx: ConversionContext) -> None:
    """Unknown input item types are dropped with a loss."""
    request = resp_req(input=[item(type="file_search_call")])
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.messages == []
    assert any(loss.reason == "unknown_item_dropped" for loss in ctx.losses)


def test_request_tools(ctx: ConversionContext) -> None:
    """Function tools map to canonical definitions."""
    request = resp_req(
        input=[],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Weather lookup",
                    "parameters": {"type": "object"},
                },
            },
            {"type": "web_search_preview"},
        ],
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.tools == [
        ToolDefinition(
            name="get_weather",
            description="Weather lookup",
            parameters={"type": "object"},
        )
    ]
    assert any(loss.reason == "non_function_tool_dropped" for loss in ctx.losses)


def test_request_scalar_options(ctx: ConversionContext) -> None:
    """Sampling, token, stream, and parallel flags map directly."""
    ir = mapper.request_to_ir(
        resp_req(
            input=[],
            temperature=0.4,
            max_output_tokens=200,
            stream=True,
            parallel_tool_calls=False,
        ),
        context=ctx,
    ).unwrap()
    assert ir.temperature == 0.4
    assert ir.max_tokens == 200
    assert ir.stream is True
    assert ir.parallel_tool_calls is False


def test_request_include_usage(ctx: ConversionContext) -> None:
    """include with usage drives include_usage and metadata."""
    ir = mapper.request_to_ir(
        resp_req(input=[], include=["usage", "citations"]), context=ctx
    ).unwrap()
    assert ir.include_usage is True
    assert ir.metadata["include"] == ["usage", "citations"]


def test_request_include_without_usage(ctx: ConversionContext) -> None:
    """include without usage leaves include_usage False."""
    ir = mapper.request_to_ir(
        resp_req(input=[], include=["citations"]), context=ctx
    ).unwrap()
    assert ir.include_usage is False


def test_request_reasoning_config(ctx: ConversionContext) -> None:
    """reasoning effort maps to ThinkingConfig and metadata."""
    reasoning = {"effort": "high"}
    ir = mapper.request_to_ir(
        resp_req(input=[], reasoning=reasoning), context=ctx
    ).unwrap()
    assert ir.thinking == ThinkingConfig(effort="high")
    assert ir.metadata["reasoning"] == reasoning


def test_request_json_object_format(ctx: ConversionContext) -> None:
    """text.json_object maps to the canonical response format."""
    text = {"format": {"type": "json_object"}}
    ir = mapper.request_to_ir(resp_req(input=[], text=text), context=ctx).unwrap()
    assert ir.response_format == {"type": "json_object"}
    assert ir.metadata["text"] == text


def test_request_json_schema_format(ctx: ConversionContext) -> None:
    """text.json_schema maps to the canonical response schema."""
    schema = {"type": "object", "properties": {"city": {"type": "string"}}}
    ir = mapper.request_to_ir(
        resp_req(
            input=[],
            text={
                "format": {"type": "json_schema", "name": "weather", "schema": schema}
            },
        ),
        context=ctx,
    ).unwrap()
    assert ir.response_format == {
        "type": "json_schema",
        "name": "weather",
        "schema": schema,
    }


def test_request_text_format_setting(ctx: ConversionContext) -> None:
    """A plain text format does not produce a response format."""
    ir = mapper.request_to_ir(
        resp_req(input=[], text={"format": {"type": "text"}}), context=ctx
    ).unwrap()
    assert ir.response_format is None
    assert ir.metadata["text"] == {"format": {"type": "text"}}


def test_request_service_tier_and_passthrough(ctx: ConversionContext) -> None:
    """service_tier, metadata, and passthrough survive conversion."""
    ir = mapper.request_to_ir(
        resp_req(input=[], service_tier="flex", passthrough={"seed": 7}),
        context=ctx,
    ).unwrap()
    assert ir.metadata["service_tier"] == "flex"
    assert ir.passthrough == {"seed": 7}


# ---------------------------------------------------------------------------
# ir_to_request
# ---------------------------------------------------------------------------


def test_ir_to_request_system(ctx: ConversionContext) -> None:
    """System text maps to instructions."""
    request = RelayRequest(model="gpt-5.2", messages=[], system="Be concise.")
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert isinstance(wire, ResponsesRequest)
    assert wire.model == "gpt-5.2"
    assert wire.instructions == "Be concise."
    assert wire.input == []


def test_ir_to_request_text_message(ctx: ConversionContext) -> None:
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


def test_ir_to_request_multi_part_message(ctx: ConversionContext) -> None:
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


def test_ir_to_request_base64_image(ctx: ConversionContext) -> None:
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


def test_ir_to_request_input_files_restored(ctx: ConversionContext) -> None:
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


def test_ir_to_request_item_id_restored(ctx: ConversionContext) -> None:
    """Per-message item ids are restored on the wire item."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[
            ChatMessage(role="user", content="hi", metadata={"item_id": "msg_9"})
        ],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.input[0].id == "msg_9"


def test_ir_to_request_tool_message(ctx: ConversionContext) -> None:
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


def test_ir_to_request_tool_calls(ctx: ConversionContext) -> None:
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
) -> None:
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


def test_ir_to_request_thinking_blocks(ctx: ConversionContext) -> None:
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


def test_ir_to_request_thinking_effort(ctx: ConversionContext) -> None:
    """Thinking effort maps to the reasoning config."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[],
        thinking=ThinkingConfig(effort="medium"),
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.reasoning == {"effort": "medium"}


def test_ir_to_request_reasoning_metadata(ctx: ConversionContext) -> None:
    """Metadata reasoning passthrough is restored."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[],
        metadata={"reasoning": {"effort": "low", "summary": "auto"}},
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.reasoning == {"effort": "low", "summary": "auto"}


def test_ir_to_request_include_usage(ctx: ConversionContext) -> None:
    """include_usage appends usage to include."""
    request = RelayRequest(model="gpt-5.2", messages=[], include_usage=True)
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.include == ["usage"]


def test_ir_to_request_include_metadata(ctx: ConversionContext) -> None:
    """Requested include fields are restored alongside usage."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[],
        include_usage=True,
        metadata={"include": ["citations"]},
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.include == ["citations", "usage"]


def test_ir_to_request_response_format(ctx: ConversionContext) -> None:
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


def test_ir_to_request_text_metadata_preserved(ctx: ConversionContext) -> None:
    """Metadata text config is echoed when no response format exists."""
    text = {"format": {"type": "text"}}
    request = RelayRequest(model="gpt-5.2", messages=[], metadata={"text": text})
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.text == text


def test_ir_to_request_scalars(ctx: ConversionContext) -> None:
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
) -> None:
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


def test_ir_to_request_web_search_restored(ctx: ConversionContext) -> None:
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


def test_ir_to_request_system_message_folds(ctx: ConversionContext) -> None:
    """System-role messages fold into instructions with a loss."""
    request = RelayRequest(
        model="gpt-5.2",
        messages=[ChatMessage(role="system", content="Rule.")],
    )
    wire = mapper.ir_to_request(request, context=ctx).unwrap()
    assert wire.instructions == "Rule."
    assert wire.input == []
    assert any(loss.reason == "system_message_reordered" for loss in ctx.losses)


# ---------------------------------------------------------------------------
# response_to_ir
# ---------------------------------------------------------------------------


def test_response_message_text(ctx: ConversionContext) -> None:
    """output_text parts become the canonical content string."""
    response = resp(
        output=[
            ResponsesItem(
                type="message",
                role="assistant",
                content=[{"type": "output_text", "text": "Hello"}],
            )
        ],
        status="completed",
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == "Hello"
    assert ir.status == "completed"
    assert ir.finish_reason == "stop"


def test_response_multiple_text_parts(ctx: ConversionContext) -> None:
    """Multiple output_text parts concatenate in order."""
    response = resp(
        output=[
            ResponsesItem(
                type="message",
                role="assistant",
                content=[
                    {"type": "output_text", "text": "A"},
                    {"type": "output_text", "text": "B"},
                ],
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == "AB"


def test_response_unknown_content_part(ctx: ConversionContext) -> None:
    """Unknown output content parts are dropped with a loss."""
    response = resp(
        output=[
            ResponsesItem(
                type="message",
                role="assistant",
                content=[
                    {"type": "output_text", "text": "A"},
                    {"type": "output_audio", "id": "au_1"},
                ],
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == "A"
    assert any(loss.reason == "unknown_part_type" for loss in ctx.losses)


def test_response_reasoning(ctx: ConversionContext) -> None:
    """Reasoning summaries map to a ThinkingResult with tokens."""
    response = resp(
        output=[
            ResponsesItem(
                type="reasoning",
                id="rs_1",
                summary=[
                    {"type": "summary_text", "text": "Step one. "},
                    {"type": "summary_text", "text": "Step two."},
                ],
            )
        ],
        usage=usage(output_tokens_details={"reasoning_tokens": 12}),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.thinking == ThinkingResult(content="Step one. Step two.", tokens=12)


def test_response_function_call(ctx: ConversionContext) -> None:
    """function_call output items become canonical tool calls."""
    response = resp(
        output=[
            ResponsesItem(
                type="function_call",
                id="fc_1",
                call_id="call_1",
                name="get_weather",
                arguments='{"city": "NYC"}',
            )
        ],
        status="completed",
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.tool_calls == [
        ToolCall(
            id="call_1",
            type="function",
            function=FunctionCall(name="get_weather", arguments={"city": "NYC"}),
        )
    ]
    assert ir.finish_reason == "tool_calls"


def test_response_function_call_invalid_arguments(
    ctx: ConversionContext,
) -> None:
    """Unparseable argument JSON is preserved verbatim."""
    response = resp(
        output=[
            ResponsesItem(
                type="function_call",
                call_id="call_1",
                name="get_weather",
                arguments="{oops",
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    function = ir.tool_calls[0].function
    assert isinstance(function, FunctionCall)
    assert function.arguments == "{oops"


def test_response_function_call_output(ctx: ConversionContext) -> None:
    """function_call_output items become tool result messages."""
    response = resp(
        output=[
            ResponsesItem(
                type="function_call_output",
                call_id="call_1",
                output="72F",
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.tool_results == [
        ChatMessage(role="tool", content="72F", tool_call_id="call_1")
    ]


def test_response_web_search_call(ctx: ConversionContext) -> None:
    """web_search_call output is preserved on passthrough."""
    search = {
        "type": "web_search_call",
        "id": "ws_1",
        "status": "completed",
    }
    response = resp(output=[ResponsesItem.from_dict(dict(search))], status="completed")
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.passthrough["web_search_calls"] == [search]
    assert any(loss.reason == "unsupported_item_preserved" for loss in ctx.losses)


def test_response_unknown_item(ctx: ConversionContext) -> None:
    """Unknown output item types are dropped with a loss."""
    response = resp(output=[ResponsesItem(type="file_search_call")])
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == ""
    assert ir.tool_calls == []
    assert any(loss.reason == "unknown_item_dropped" for loss in ctx.losses)


def test_response_incomplete_max_tokens(ctx: ConversionContext) -> None:
    """Incomplete max_output_tokens maps to canonical length."""
    response = resp(
        output=[],
        status="incomplete",
        incomplete_details=ResponsesIncompleteDetails(reason="max_output_tokens"),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason == "length"
    assert ir.status == "incomplete"
    assert ir.incomplete_details == {"reason": "max_output_tokens"}


def test_response_incomplete_content_filter(ctx: ConversionContext) -> None:
    """Incomplete content_filter maps to canonical content_filter."""
    response = resp(
        output=[],
        status="incomplete",
        incomplete_details=ResponsesIncompleteDetails(reason="content_filter"),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason == "content_filter"


def test_response_failed(ctx: ConversionContext) -> None:
    """A failed response maps to the other finish reason."""
    response = resp(output=[], status="failed")
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason == "other"


def test_response_in_progress(ctx: ConversionContext) -> None:
    """An in-progress status leaves finish reason unset."""
    response = resp(output=[], status="in_progress")
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason is None


def test_response_usage(ctx: ConversionContext) -> None:
    """Usage maps with cached and reasoning token details."""
    response = resp(
        output=[],
        usage=usage(
            input_tokens=20,
            output_tokens=7,
            input_tokens_details={"cached_tokens": 6},
            output_tokens_details={"reasoning_tokens": 3},
        ),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.usage is not None
    assert ir.usage.prompt_tokens == 20
    assert ir.usage.completion_tokens == 7
    assert ir.usage.cache_read_tokens == 6
    assert ir.usage.reasoning_tokens == 3


def test_response_headers_and_error(ctx: ConversionContext) -> None:
    """Response ids, error, and passthrough survive conversion."""
    response = resp(
        output=[],
        id="resp_1",
        model="gpt-5.2",
        created_at=1234,
        error={"code": "rate_limit_exceeded", "message": "slow down"},
        passthrough={"reason": {"code": "x"}},
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.id == "resp_1"
    assert ir.model == "gpt-5.2"
    assert ir.created == 1234
    assert ir.passthrough["error"] == {
        "code": "rate_limit_exceeded",
        "message": "slow down",
    }
    assert ir.passthrough["reason"] == {"code": "x"}


# ---------------------------------------------------------------------------
# ir_to_response
# ---------------------------------------------------------------------------


def _assert_item(
    items: list[ResponsesItem], index: int, **fields: Any
) -> ResponsesItem:
    """Assert one wire item matches the expected fields."""
    actual = items[index]
    for key, value in fields.items():
        assert getattr(actual, key) == value, f"{key}: {getattr(actual, key)!r}"
    return actual


def test_ir_to_response_content(ctx: ConversionContext) -> None:
    """Content emits an assistant message with output_text parts."""
    response = RelayResponse(model="gpt-5.2", content="Hi", finish_reason="stop")
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    assert isinstance(wire, ResponsesResponse)
    assert wire.id.startswith("chatcmpl-")
    assert wire.object == "response"
    _assert_item(
        wire.output,
        0,
        type="message",
        role="assistant",
        content=[{"type": "output_text", "text": "Hi", "annotations": []}],
    )


def test_ir_to_response_thinking_first(ctx: ConversionContext) -> None:
    """Thinking items follow content in the output ordering."""
    response = RelayResponse(
        model="gpt-5.2",
        content="Answer",
        thinking=ThinkingResult(content="Analysis"),
        finish_reason="stop",
    )
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    _assert_item(wire.output, 0, type="message", role="assistant")
    _assert_item(
        wire.output,
        1,
        type="reasoning",
        content=[{"type": "summary_text", "text": "Analysis", "annotations": None}],
    )


def test_ir_to_response_tool_calls(ctx: ConversionContext) -> None:
    """Tool calls emit function_call items with JSON arguments."""
    response = RelayResponse(
        model="gpt-5.2",
        content="",
        tool_calls=[
            ToolCall(
                id="call_1",
                type="function",
                function=FunctionCall(name="get_weather", arguments={"city": "SF"}),
            )
        ],
        finish_reason="tool_calls",
    )
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    call = wire.output[0]
    assert call.type == "function_call"
    assert call.call_id == "call_1"
    assert call.name == "get_weather"
    assert call.arguments == '{"city":"SF"}'


def test_ir_to_response_tool_results(ctx: ConversionContext) -> None:
    """Tool results emit function_call_output items."""
    response = RelayResponse(
        model="gpt-5.2",
        content="",
        tool_results=[ChatMessage(role="tool", content="72F", tool_call_id="call_1")],
        finish_reason="tool_calls",
    )
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    _assert_item(
        wire.output,
        0,
        type="function_call_output",
        call_id="call_1",
        output="72F",
    )


def test_ir_to_response_finish_length(ctx: ConversionContext) -> None:
    """Canonical length maps to incomplete with max output tokens."""
    response = RelayResponse(model="gpt-5.2", content="x", finish_reason="length")
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    assert wire.status == "incomplete"
    assert wire.incomplete_details is not None
    assert wire.incomplete_details.reason == "max_output_tokens"


def test_ir_to_response_finish_content_filter(ctx: ConversionContext) -> None:
    """Canonical content_filter maps to incomplete details."""
    response = RelayResponse(
        model="gpt-5.2", content="x", finish_reason="content_filter"
    )
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    assert wire.status == "incomplete"
    assert wire.incomplete_details.to_dict()["reason"] == "content_filter"


def test_ir_to_response_finish_stop(ctx: ConversionContext) -> None:
    """Canonical stop maps to a completed response."""
    response = RelayResponse(model="gpt-5.2", content="x", finish_reason="stop")
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    assert wire.status == "completed"
    assert wire.incomplete_details is None


def test_ir_to_response_status_override(ctx: ConversionContext) -> None:
    """An explicit status wins over the derived status."""
    response = RelayResponse(
        model="gpt-5.2",
        content="x",
        status="in_progress",
        incomplete_details={"reason": "max_output_tokens"},
    )
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    assert wire.status == "in_progress"
    assert wire.incomplete_details.to_dict() == {"reason": "max_output_tokens"}


def test_ir_to_response_headers(ctx: ConversionContext) -> None:
    """Id, model, created, object, and error restore on the wire."""
    response = RelayResponse(
        model="gpt-5.2",
        id="resp_1",
        created=99,
        content="x",
        passthrough={"object": "response.list_item", "error": {"code": "x"}},
    )
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    assert wire.id == "resp_1"
    assert wire.created_at == 99
    assert wire.object == "response.list_item"
    assert wire.error == {"code": "x"}
    assert wire.passthrough == {}


def test_ir_to_response_usage(ctx: ConversionContext) -> None:
    """Usage restores with cached and reasoning details."""
    response = RelayResponse(
        model="gpt-5.2",
        content="x",
        usage=RelayUsage(
            prompt_tokens=10,
            completion_tokens=5,
            cache_read_tokens=4,
            reasoning_tokens=3,
        ),
    )
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    assert wire.usage is not None
    assert wire.usage.input_tokens == 10
    assert wire.usage.output_tokens == 5
    assert wire.usage.total_tokens == 15
    assert wire.usage.input_tokens_details == {"cached_tokens": 4}
    assert wire.usage.completion_tokens_details == {"reasoning_tokens": 3}


# ---------------------------------------------------------------------------
# stream ops
# ---------------------------------------------------------------------------


def test_stream_to_delta_unsupported(ctx: ConversionContext) -> None:
    """Stream conversion is deferred to the shared lifecycle task."""
    state = StreamState(
        source=RelayFormat.OPENAI_RESPONSES,
        target=RelayFormat.OPENAI_RESPONSES,
        model="gpt-5.2",
    )
    result = mapper.stream_to_delta(
        ResponsesEvent(type="response.output_text.delta"),
        state=state,
    )
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FEATURE.value


def test_delta_to_stream_unsupported(ctx: ConversionContext) -> None:
    """Stream emission is deferred to the shared lifecycle task."""
    state = StreamState(
        source=RelayFormat.OPENAI_RESPONSES,
        target=RelayFormat.OPENAI_RESPONSES,
        model="gpt-5.2",
    )
    result = mapper.delta_to_stream(delta=object(), state=state)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FEATURE.value
