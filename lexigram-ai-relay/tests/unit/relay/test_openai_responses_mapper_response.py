"""Tests for the OpenAI Responses request/response mapper."""

from __future__ import annotations

from lexigram.ai.relay.context import ConversionContext
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.llm import ChatMessage, FunctionCall, ToolCall
from lexigram.contracts.ai.relay.dto import ResponsesEvent, ResponsesIncompleteDetails, ResponsesItem, ResponsesResponse
from lexigram.contracts.ai.relay.ir import RelayResponse, StreamState
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.ai.thinking import ThinkingResult
from typing import Any

def test_response_message_text(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
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

def test_response_multiple_text_parts(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
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

def test_response_unknown_content_part(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
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

def test_response_reasoning(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any, usage: Any) -> None:
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

def test_response_function_call(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
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
*, mapper: OpenAIResponsesMapper, resp: Any) -> None:
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

def test_response_function_call_output(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
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

def test_response_web_search_call(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
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

def test_response_unknown_item(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
    """Unknown output item types are dropped with a loss."""
    response = resp(output=[ResponsesItem(type="file_search_call")])
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == ""
    assert ir.tool_calls == []
    assert any(loss.reason == "unknown_item_dropped" for loss in ctx.losses)

def test_response_incomplete_max_tokens(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
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

def test_response_incomplete_content_filter(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
    """Incomplete content_filter maps to canonical content_filter."""
    response = resp(
        output=[],
        status="incomplete",
        incomplete_details=ResponsesIncompleteDetails(reason="content_filter"),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason == "content_filter"

def test_response_failed(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
    """A failed response maps to the other finish reason."""
    response = resp(output=[], status="failed")
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason == "other"

def test_response_in_progress(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
    """An in-progress status leaves finish reason unset."""
    response = resp(output=[], status="in_progress")
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason is None

def test_response_usage(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any, usage: Any) -> None:
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

def test_response_headers_and_error(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper, resp: Any) -> None:
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

def _assert_item(
    items: list[ResponsesItem], index: int, **fields: Any
) -> ResponsesItem:
    """Assert one wire item matches the expected fields."""
    actual = items[index]
    for key, value in fields.items():
        assert getattr(actual, key) == value, f"{key}: {getattr(actual, key)!r}"
    return actual

def test_ir_to_response_content(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
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

def test_ir_to_response_thinking_first(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
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

def test_ir_to_response_tool_calls(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
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

def test_ir_to_response_tool_results(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
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

def test_ir_to_response_finish_length(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Canonical length maps to incomplete with max output tokens."""
    response = RelayResponse(model="gpt-5.2", content="x", finish_reason="length")
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    assert wire.status == "incomplete"
    assert wire.incomplete_details is not None
    assert wire.incomplete_details.reason == "max_output_tokens"

def test_ir_to_response_finish_content_filter(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Canonical content_filter maps to incomplete details."""
    response = RelayResponse(
        model="gpt-5.2", content="x", finish_reason="content_filter"
    )
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    assert wire.status == "incomplete"
    assert wire.incomplete_details.to_dict()["reason"] == "content_filter"

def test_ir_to_response_finish_stop(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Canonical stop maps to a completed response."""
    response = RelayResponse(model="gpt-5.2", content="x", finish_reason="stop")
    wire = mapper.ir_to_response(response, context=ctx).unwrap()
    assert wire.status == "completed"
    assert wire.incomplete_details is None

def test_ir_to_response_status_override(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
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

def test_ir_to_response_headers(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
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

def test_ir_to_response_usage(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
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

def test_stream_to_delta_unsupported(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
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

def test_delta_to_stream_unsupported(ctx: ConversionContext, *, mapper: OpenAIResponsesMapper) -> None:
    """Stream emission is deferred to the shared lifecycle task."""
    state = StreamState(
        source=RelayFormat.OPENAI_RESPONSES,
        target=RelayFormat.OPENAI_RESPONSES,
        model="gpt-5.2",
    )
    result = mapper.delta_to_stream(delta=object(), state=state)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FEATURE.value
