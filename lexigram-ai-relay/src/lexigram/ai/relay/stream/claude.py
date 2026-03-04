"""Anthropic Claude Messages target stream emitter.

Maps one canonical :class:`StreamDelta` into valid Claude SSE events.
The emitter owns the block lifecycle: each text, thinking, and tool-use
block is started once, closed exactly once, and the terminal
``message_delta``/``message_stop`` pair is emitted once.  Usage rides on
``message_delta`` so the included usage shape matches the target wire
format.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.errors import stream_state_invalid
from lexigram.ai.relay.finish_reasons import (
    finish_reason_to_wire,
    normalize_finish_reason,
)
from lexigram.ai.relay.stream.state import (
    StreamSnapshot,
    StreamToolCallRecord,
    _first_tool_contribution,
    _pre_text,
    _pre_thinking,
    _pre_tool_indices,
    _started_pre,
)
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.dto import (
    ClaudeContent,
    ClaudeResponse,
    ClaudeStreamEvent,
    ClaudeUsage,
)
from lexigram.contracts.ai.relay.ir import StreamDelta
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = ["claude_emitter"]


def _claude_stop_reason(reason: str) -> str:
    """Map a canonical finish reason onto Claude's wire values."""
    return finish_reason_to_wire(normalize_finish_reason(reason), RelayFormat.CLAUDE)


def _usage_to_wire(usage: RelayUsage) -> ClaudeUsage:
    """Serialize canonical usage into the Claude usage shape."""
    return ClaudeUsage(
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens,
        cache_creation_input_tokens=usage.cache_creation_tokens,
        cache_read_input_tokens=usage.cache_read_tokens,
    )


def _message_start(
    state: StreamSnapshot, *, role: str = "assistant"
) -> ClaudeStreamEvent:
    """Build the ``message_start`` event with a message snapshot."""
    return ClaudeStreamEvent(
        type="message_start",
        message=ClaudeResponse(
            id=state.stream_id or "",
            type="message",
            role=role,
            model=state.model,
            content=[],
            usage=(
                _usage_to_wire(state.usage)
                if state.usage is not None
                else ClaudeUsage()
            ),
        ),
    )


def _tool_record(state: StreamSnapshot, index: int) -> StreamToolCallRecord | None:
    return next((r for r in state.tool_calls if r.index == index), None)


def _thinking_open_pre(state: StreamSnapshot, delta: StreamDelta) -> bool:
    """Whether a thinking block was already open before this delta."""
    pre_thinking = _pre_thinking(state, delta)
    return (
        bool(pre_thinking)
        and not _pre_text(state, delta)
        and not _pre_tool_indices(state, delta)
    )


def _text_open_pre(state: StreamSnapshot, delta: StreamDelta) -> bool:
    """Whether a text block was already open before this delta."""
    return bool(_pre_text(state, delta)) and not _pre_tool_indices(state, delta)


def _thinking_block_index(state: StreamSnapshot) -> int:
    """Deterministic Claude block index for the thinking block."""
    return int(bool(state.text)) + len(state.tool_calls)


def _text_block_index(state: StreamSnapshot) -> int:
    """Deterministic Claude block index for the text block."""
    return int(bool(state.thinking_text)) + len(state.tool_calls)


def _thinking_reopen_index(state: StreamSnapshot) -> int:
    """Block index for a reopened thinking block."""
    return int(bool(state.text)) + 1 + len(state.tool_calls)


def _text_reopen_index(state: StreamSnapshot) -> int:
    """Block index for a reopened text block."""
    return int(bool(state.thinking_text)) + 1 + len(state.tool_calls)


def _tool_block_index(state: StreamSnapshot, position: int) -> int:
    """Deterministic Claude block index for a tool-use block."""
    return int(bool(state.thinking_text)) + int(bool(state.text)) + position


def _tool_position(state: StreamSnapshot, index: int) -> int:
    """Position of a tool call among the stream's tool call records."""
    for position, record in enumerate(state.tool_calls):
        if record.index == index:
            return position
    return len(state.tool_calls) - 1


def _content_block_stop(index: int) -> ClaudeStreamEvent:
    return ClaudeStreamEvent(type="content_block_stop", index=index)


def _close_open(state: StreamSnapshot, delta: StreamDelta) -> list[ClaudeStreamEvent]:
    """Close the single currently-open content block, if any.

    The close index must match the index the block was opened with, so it
    is reconstructed from the pre-delta state (the block's content types
    cannot change between its start and its stop).
    """
    pre_text = _pre_text(state, delta)
    pre_thinking = _pre_thinking(state, delta)
    pre_tools = _pre_tool_indices(state, delta)
    if bool(pre_thinking) and not pre_text and not pre_tools:
        return [_content_block_stop(int(bool(pre_text)) + len(pre_tools))]
    if pre_text and not pre_tools:
        return [_content_block_stop(int(bool(pre_thinking)) + len(pre_tools))]
    if pre_tools:
        ordered = [r.index for r in state.tool_calls if r.index in pre_tools]
        last = ordered[-1] if ordered else 0
        position = _tool_position(state, last)
        return [
            _content_block_stop(
                int(bool(pre_thinking)) + int(bool(pre_text)) + position
            )
        ]
    return []


def _thinking_signature(delta: StreamDelta) -> str | None:
    signature = delta.passthrough.get("signature")
    return signature if isinstance(signature, str) and signature else None


def _text_events(state: StreamSnapshot, delta: StreamDelta) -> list[ClaudeStreamEvent]:
    events: list[ClaudeStreamEvent] = []
    if not delta.content:
        return events
    first = state.text == delta.content
    if first:
        events.extend(_close_open(state, delta))
        index = _text_block_index(state)
        events.append(
            ClaudeStreamEvent(
                type="content_block_start",
                index=index,
                content_block=ClaudeContent(type="text", text=""),
            )
        )
    elif _text_open_pre(state, delta):
        index = _text_block_index(state)
    else:
        events.extend(_close_open(state, delta))
        index = _text_reopen_index(state)
        events.append(
            ClaudeStreamEvent(
                type="content_block_start",
                index=index,
                content_block=ClaudeContent(type="text", text=""),
            )
        )
    events.append(
        ClaudeStreamEvent(
            type="content_block_delta",
            index=index,
            delta={"type": "text_delta", "text": delta.content},
        )
    )
    return events


def _thinking_events(
    state: StreamSnapshot, delta: StreamDelta
) -> list[ClaudeStreamEvent]:
    events: list[ClaudeStreamEvent] = []
    if not delta.thinking_delta:
        return events
    first = state.thinking_text == delta.thinking_delta
    if first:
        events.extend(_close_open(state, delta))
        index = _thinking_block_index(state)
        events.append(
            ClaudeStreamEvent(
                type="content_block_start",
                index=index,
                content_block=ClaudeContent(type="thinking", thinking=""),
            )
        )
    elif _thinking_open_pre(state, delta):
        index = _thinking_block_index(state)
    else:
        events.extend(_close_open(state, delta))
        index = _thinking_reopen_index(state)
        events.append(
            ClaudeStreamEvent(
                type="content_block_start",
                index=index,
                content_block=ClaudeContent(type="thinking", thinking=""),
            )
        )
    signature = _thinking_signature(delta)
    thinking_delta_payload: dict[str, Any] = {
        "type": "thinking_delta",
        "thinking": delta.thinking_delta,
    }
    if signature is not None:
        thinking_delta_payload["signature"] = signature
    events.append(
        ClaudeStreamEvent(
            type="content_block_delta",
            index=index,
            delta=thinking_delta_payload,
        )
    )
    return events


def _tool_events(state: StreamSnapshot, delta: StreamDelta) -> list[ClaudeStreamEvent]:
    events: list[ClaudeStreamEvent] = []
    index = delta.tool_call_index
    if index is None:
        return events
    record = _tool_record(state, index)
    if record is None:
        return events
    first = _first_tool_contribution(state, delta)
    if first:
        events.extend(_close_open(state, delta))
    position = _tool_position(state, index)
    block_index = _tool_block_index(state, position)
    if first:
        events.append(
            ClaudeStreamEvent(
                type="content_block_start",
                index=block_index,
                content_block=ClaudeContent(
                    type="tool_use",
                    tool_use_id=record.id,
                    name=record.name,
                    input={},
                ),
            )
        )
    if delta.tool_call_arguments is not None:
        events.append(
            ClaudeStreamEvent(
                type="content_block_delta",
                index=block_index,
                delta={
                    "type": "input_json_delta",
                    "partial_json": delta.tool_call_arguments,
                },
            )
        )
    return events


def _finish_events(
    state: StreamSnapshot, delta: StreamDelta
) -> list[ClaudeStreamEvent]:
    events: list[ClaudeStreamEvent] = []
    events.extend(_close_open(state, delta))
    reason = _claude_stop_reason(delta.finish_reason or "stop")
    usage = _usage_to_wire(state.usage) if state.usage is not None else None
    events.append(
        ClaudeStreamEvent(
            type="message_delta",
            delta={"stop_reason": reason},
            usage=usage,
        )
    )
    events.append(ClaudeStreamEvent(type="message_stop"))
    return events


def _usage_events(state: StreamSnapshot, delta: StreamDelta) -> list[ClaudeStreamEvent]:
    return []


def claude_emitter(
    delta: StreamDelta, *, state: StreamSnapshot
) -> Result[tuple[ClaudeStreamEvent, ...], RelayError]:
    """Map one canonical delta into Claude SSE events.

    Args:
        delta: One canonical stream delta.
        state: Accumulated session snapshot.

    Returns:
        Ok(tuple of events) on success; ``stream_state_invalid`` for an
        unknown delta kind.
    """
    if delta.kind == "role":
        events: list[ClaudeStreamEvent] = []
        if not _started_pre(state, delta):
            events.append(_message_start(state))
        return Ok(tuple(events))
    if delta.kind == "content":
        events = []
        if not _started_pre(state, delta):
            events.append(_message_start(state))
        events.extend(_text_events(state, delta))
        return Ok(tuple(events))
    if delta.kind == "thinking":
        events = []
        if not _started_pre(state, delta):
            events.append(_message_start(state))
        events.extend(_thinking_events(state, delta))
        return Ok(tuple(events))
    if delta.kind == "tool_call":
        events = []
        if not _started_pre(state, delta):
            events.append(_message_start(state))
        events.extend(_tool_events(state, delta))
        return Ok(tuple(events))
    if delta.kind == "finish":
        events = []
        if not _started_pre(state, delta):
            events.append(_message_start(state))
        events.extend(_finish_events(state, delta))
        return Ok(tuple(events))
    if delta.kind == "usage":
        return Ok(tuple(_usage_events(state, delta)))
    if delta.kind == "status":
        return Ok(())
    return Err(stream_state_invalid(f"unknown delta kind {delta.kind!r} for claude"))
