"""Tests for the OpenAI Responses request/response mapper."""

from __future__ import annotations

from lexigram.ai.relay.context import ConversionContext
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.multimodal import ImageUrlPart, TextPart
from lexigram.contracts.ai.relay.dto import ResponsesItem
from lexigram.contracts.ai.thinking import ThinkingConfig

def test_request_string_input(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """A plain string input becomes a single user message."""
    ir = mapper.request_to_ir(resp_req(input="Hello there"), context=ctx).unwrap()
    assert ir.model == "gpt-5.2"
    assert ir.messages == [ChatMessage(role="user", content="Hello there")]
    assert ir.system is None

def test_request_message_text_collapses(ctx: ConversionContext, *, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """A single input_text part collapses to a plain string."""
    request = resp_req(
        input=[item(role="user", content=[{"type": "input_text", "text": "hi"}])]
    )
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.messages[0].role == "user"
    assert ir.messages[0].content == "hi"
    assert ir.messages[0].metadata is None

def test_request_message_item_id_preserved(ctx: ConversionContext, *, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """The item id is preserved on message metadata."""
    request = resp_req(input=[item(id="msg_1")])
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.messages[0].metadata == {"item_id": "msg_1"}

def test_request_text_and_image_parts(ctx: ConversionContext, *, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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

def test_request_input_file_preserved(ctx: ConversionContext, *, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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

def test_request_system_message_folds(ctx: ConversionContext, *, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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

def test_request_system_message_reordered_loss(ctx: ConversionContext, *, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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

def test_request_instructions(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """Instructions map to the canonical system field."""
    ir = mapper.request_to_ir(
        resp_req(instructions="You are helpful.", input="hi"), context=ctx
    ).unwrap()
    assert ir.system == "You are helpful."

def test_request_function_call_item(ctx: ConversionContext, *, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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
*, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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
*, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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

def test_request_function_call_output(ctx: ConversionContext, *, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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

def test_request_tool_turn_order(ctx: ConversionContext, *, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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

def test_request_reasoning_item(ctx: ConversionContext, *, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """Reasoning summaries are preserved as raw thinking blocks."""
    summary = [{"type": "summary_text", "text": "Step by step..."}]
    request = resp_req(input=[item(type="reasoning", id="rs_1", summary=summary)])
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    message = ir.messages[0]
    assert message.role == "assistant"
    assert message.content == ""
    assert message.thinking_blocks == summary
    assert message.metadata == {"item_id": "rs_1"}

def test_request_web_search_call_preserved(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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

def test_request_unknown_item_dropped(ctx: ConversionContext, *, item: Any, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """Unknown input item types are dropped with a loss."""
    request = resp_req(input=[item(type="file_search_call")])
    ir = mapper.request_to_ir(request, context=ctx).unwrap()
    assert ir.messages == []
    assert any(loss.reason == "unknown_item_dropped" for loss in ctx.losses)

def test_request_tools(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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

def test_request_scalar_options(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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

def test_request_include_usage(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """include with usage drives include_usage and metadata."""
    ir = mapper.request_to_ir(
        resp_req(input=[], include=["usage", "citations"]), context=ctx
    ).unwrap()
    assert ir.include_usage is True
    assert ir.metadata["include"] == ["usage", "citations"]

def test_request_include_without_usage(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """include without usage leaves include_usage False."""
    ir = mapper.request_to_ir(
        resp_req(input=[], include=["citations"]), context=ctx
    ).unwrap()
    assert ir.include_usage is False

def test_request_reasoning_config(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """reasoning effort maps to ThinkingConfig and metadata."""
    reasoning = {"effort": "high"}
    ir = mapper.request_to_ir(
        resp_req(input=[], reasoning=reasoning), context=ctx
    ).unwrap()
    assert ir.thinking == ThinkingConfig(effort="high")
    assert ir.metadata["reasoning"] == reasoning

def test_request_json_object_format(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """text.json_object maps to the canonical response format."""
    text = {"format": {"type": "json_object"}}
    ir = mapper.request_to_ir(resp_req(input=[], text=text), context=ctx).unwrap()
    assert ir.response_format == {"type": "json_object"}
    assert ir.metadata["text"] == text

def test_request_json_schema_format(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
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

def test_request_text_format_setting(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """A plain text format does not produce a response format."""
    ir = mapper.request_to_ir(
        resp_req(input=[], text={"format": {"type": "text"}}), context=ctx
    ).unwrap()
    assert ir.response_format is None
    assert ir.metadata["text"] == {"format": {"type": "text"}}

def test_request_service_tier_and_passthrough(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp_req: Any) -> None:
    """service_tier, metadata, and passthrough survive conversion."""
    ir = mapper.request_to_ir(
        resp_req(input=[], service_tier="flex", passthrough={"seed": 7}),
        context=ctx,
    ).unwrap()
    assert ir.metadata["service_tier"] == "flex"
    assert ir.passthrough == {"seed": 7}
