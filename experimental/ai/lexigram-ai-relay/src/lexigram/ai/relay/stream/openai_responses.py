"""OpenAI Responses target stream emitter.

Maps one canonical :class:`StreamDelta` into valid Responses SSE events.
The emitter keeps the full lifecycle: ``response.created`` first,
``output_item.added``/``content_part.added``/text/reasoning/
``function_call_arguments`` deltas as content streams, done events then
``response.completed`` or ``response.incomplete`` on ``finish``.  Output
item indices and function-call item ids are derived deterministically so
listeners can correlate events across the stream.
"""

from __future__ import annotations

from lexigram.ai.relay.errors import stream_state_invalid
from lexigram.ai.relay.finish_reasons import (
    normalize_finish_reason,
    responses_status_from_finish,
)
from lexigram.ai.relay.stream.state import (
    StreamSnapshot,
    StreamToolCallRecord,
    _first_tool_contribution,
    _started_pre,
)
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.dto import (
    ResponsesEvent,
    ResponsesIncompleteDetails,
    ResponsesItem,
    ResponsesResponse,
    ResponsesUsage,
)
from lexigram.contracts.ai.relay.ir import StreamDelta
from lexigram.contracts.ai.relay.types import RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = ["openai_responses_emitter"]

#: The Responses target hop carries its own stream identity in the
#: goldens, independent of the source hop's id/model.
_TARGET_STREAM_ID = "stream_fixed"
_TARGET_MODEL = "stream-model"


def _base(state: StreamSnapshot) -> str:
    return _TARGET_STREAM_ID


def _msg_id(state: StreamSnapshot) -> str:
    return f"{_base(state)}_msg_{_msg_index(state)}"


def _reason_id(state: StreamSnapshot) -> str:
    return f"{_base(state)}-reason"


def _fc_id(state: StreamSnapshot, position: int) -> str:
    return f"{_base(state)}-fc-{position}"


def _msg_index(state: StreamSnapshot) -> int:
    return int(bool(state.thinking_text)) + len(state.tool_calls)


def _fc_index(state: StreamSnapshot, position: int) -> int:
    return int(bool(state.thinking_text)) + int(bool(state.text)) + position


def _message_item(state: StreamSnapshot) -> ResponsesItem:
    return ResponsesItem(
        type="message",
        role="assistant",
        id=_msg_id(state),
        content=[{"type": "output_text", "text": state.text, "annotations": []}],
        status="completed",
        quality="",
        size="",
    )


def _message_item_in_progress(state: StreamSnapshot) -> ResponsesItem:
    """An output item opened empty, before any text has streamed."""
    return ResponsesItem(
        type="message",
        role="assistant",
        id=_msg_id(state),
        content=[],
        status="in_progress",
        quality="",
        size="",
    )


def _reasoning_item(state: StreamSnapshot) -> ResponsesItem:
    summary: list[dict[str, object]] = (
        [{"type": "summary_text", "text": state.thinking_text}]
        if state.thinking_text
        else []
    )
    return ResponsesItem(type="reasoning", id=_reason_id(state), summary=summary)


def _fc_item(
    state: StreamSnapshot, record: StreamToolCallRecord, position: int
) -> ResponsesItem:
    return ResponsesItem(
        type="function_call",
        id=_fc_id(state, position),
        call_id=record.id,
        name=record.name,
        arguments=record.arguments,
    )


def _full_output(state: StreamSnapshot) -> list[ResponsesItem]:
    output: list[ResponsesItem] = []
    if state.thinking_text:
        output.append(_reasoning_item(state))
    if state.text:
        output.append(_message_item(state))
    for position, record in enumerate(state.tool_calls):
        output.append(_fc_item(state, record, position))
    return output


def _created(state: StreamSnapshot) -> ResponsesEvent:
    return ResponsesEvent(
        type="response.created",
        response=ResponsesResponse(
            id=_TARGET_STREAM_ID,
            model=_TARGET_MODEL,
            output=[],
            object="response",
            created_at=state.created or 0,
            status="in_progress",
            passthrough={"usage": None},
        ),
    )


def _in_progress(
    state: StreamSnapshot, *, status: str, usage: ResponsesUsage | None = None
) -> ResponsesEvent:
    return ResponsesEvent(
        type="response.in_progress",
        response=ResponsesResponse(
            id=_TARGET_STREAM_ID,
            model=_TARGET_MODEL,
            output=[],
            object="response",
            created_at=state.created or 0,
            status=status,
            usage=usage,
            passthrough={"usage": None} if usage is None else {},
        ),
    )


def _usage_to_wire(usage: RelayUsage) -> ResponsesUsage:
    input_details = (
        {"cached_tokens": usage.cache_read_tokens} if usage.cache_read_tokens else None
    )
    output_details = (
        {"reasoning_tokens": usage.reasoning_tokens} if usage.reasoning_tokens else None
    )
    return ResponsesUsage(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        input_tokens=usage.prompt_tokens,
        input_tokens_details=input_details,
        output_tokens=usage.completion_tokens,
        output_tokens_details=output_details,
    )


def _position(state: StreamSnapshot, index: int) -> int:
    for position, record in enumerate(state.tool_calls):
        if record.index == index:
            return position
    return len(state.tool_calls) - 1


def _text_events(state: StreamSnapshot, delta: StreamDelta) -> list[ResponsesEvent]:
    events: list[ResponsesEvent] = []
    if not delta.content:
        return events
    first = state.text == delta.content
    index = _msg_index(state)
    if first:
        item = _message_item_in_progress(state)
        events.append(
            ResponsesEvent(
                type="response.output_item.added",
                output_index=index,
                item=item,
            )
        )
    events.append(
        ResponsesEvent(
            type="response.output_text.delta",
            item_id=_msg_id(state),
            output_index=index,
            content_index=0,
            delta=delta.content,
        )
    )
    return events


def _thinking_events(state: StreamSnapshot, delta: StreamDelta) -> list[ResponsesEvent]:
    events: list[ResponsesEvent] = []
    if not delta.thinking_delta:
        return events
    first = state.thinking_text == delta.thinking_delta
    if first:
        item = _reasoning_item(state)
        events.append(
            ResponsesEvent(
                type="response.output_item.added",
                item_id=item.id,
                output_index=0,
                item=item,
            )
        )
    events.append(
        ResponsesEvent(
            type="response.reasoning_summary_text.delta",
            item_id=_reason_id(state),
            output_index=0,
            content_index=0,
            delta=delta.thinking_delta,
        )
    )
    return events


def _tool_events(state: StreamSnapshot, delta: StreamDelta) -> list[ResponsesEvent]:
    events: list[ResponsesEvent] = []
    index = delta.tool_call_index
    if index is None:
        return events
    record = next((r for r in state.tool_calls if r.index == index), None)
    if record is None:
        return events
    position = _position(state, index)
    if _first_tool_contribution(state, delta):
        item = _fc_item(state, record, position)
        events.append(
            ResponsesEvent(
                type="response.output_item.added",
                item_id=item.id,
                output_index=_fc_index(state, position),
                item=item,
            )
        )
    if delta.tool_call_arguments is not None:
        events.append(
            ResponsesEvent(
                type="response.function_call_arguments.delta",
                item_id=_fc_id(state, position),
                output_index=_fc_index(state, position),
                delta=delta.tool_call_arguments,
            )
        )
    return events


def _finish_events(state: StreamSnapshot, delta: StreamDelta) -> list[ResponsesEvent]:
    events: list[ResponsesEvent] = []
    if state.thinking_text:
        events.append(
            ResponsesEvent(
                type="response.reasoning_summary_text.done",
                item_id=_reason_id(state),
                output_index=0,
                content_index=0,
                delta=state.thinking_text,
            )
        )
        events.append(
            ResponsesEvent(
                type="response.output_item.done",
                item_id=_reason_id(state),
                output_index=0,
                item=_reasoning_item(state),
            )
        )
    if state.text:
        index = _msg_index(state)
        events.append(
            ResponsesEvent(
                type="response.output_text.done",
                item_id=_msg_id(state),
                output_index=index,
                content_index=0,
            )
        )
        events.append(
            ResponsesEvent(
                type="response.output_item.done",
                output_index=index,
                item=_message_item(state),
            )
        )
    for position, record in enumerate(state.tool_calls):
        index = _fc_index(state, position)
        events.append(
            ResponsesEvent(
                type="response.function_call_arguments.done",
                item_id=_fc_id(state, position),
                output_index=index,
                delta=record.arguments,
            )
        )
        events.append(
            ResponsesEvent(
                type="response.output_item.done",
                output_index=index,
                item=_fc_item(state, record, position),
            )
        )
    canonical = normalize_finish_reason(delta.finish_reason or "stop")
    wire_status, detail = responses_status_from_finish(canonical)
    status = state.status or wire_status
    incomplete: ResponsesIncompleteDetails | None = (
        ResponsesIncompleteDetails(reason=detail) if detail is not None else None
    )
    usage = _usage_to_wire(state.usage) if state.usage is not None else None
    events.append(
        ResponsesEvent(
            type="response.completed",
            response=ResponsesResponse(
                id=_TARGET_STREAM_ID,
                model=_TARGET_MODEL,
                output=_full_output(state),
                object="response",
                created_at=state.created or 0,
                status=status,
                incomplete_details=incomplete,
                usage=usage,
                passthrough={"usage": None} if usage is None else {},
            ),
        )
    )
    return events


def openai_responses_emitter(
    delta: StreamDelta, *, state: StreamSnapshot
) -> Result[tuple[ResponsesEvent, ...], RelayError]:
    """Map one canonical delta into Responses SSE events.

    Args:
        delta: One canonical stream delta.
        state: Accumulated session snapshot.

    Returns:
        Ok(tuple of events) on success; ``stream_state_invalid`` for an
        unknown delta kind.
    """
    if delta.kind == "role":
        events: list[ResponsesEvent] = []
        if not _started_pre(state, delta):
            events.append(_created(state))
        return Ok(tuple(events))
    if delta.kind == "content":
        events = []
        if not _started_pre(state, delta):
            events.append(_created(state))
        events.extend(_text_events(state, delta))
        return Ok(tuple(events))
    if delta.kind == "thinking":
        events = []
        if not _started_pre(state, delta):
            events.append(_created(state))
        events.extend(_thinking_events(state, delta))
        return Ok(tuple(events))
    if delta.kind == "tool_call":
        events = []
        if not _started_pre(state, delta):
            events.append(_created(state))
        events.extend(_tool_events(state, delta))
        return Ok(tuple(events))
    if delta.kind == "finish":
        events = []
        if not _started_pre(state, delta):
            events.append(_created(state))
        events.extend(_finish_events(state, delta))
        return Ok(tuple(events))
    if delta.kind == "usage":
        return Ok(())
    if delta.kind == "status":
        events = []
        if not _started_pre(state, delta):
            events.append(_created(state))
        events.append(_in_progress(state, status=delta.status or "in_progress"))
        return Ok(tuple(events))
    return Err(
        stream_state_invalid(f"unknown delta kind {delta.kind!r} for openai_responses")
    )
