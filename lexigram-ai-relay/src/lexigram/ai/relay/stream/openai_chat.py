"""OpenAI Chat Completions target stream emitter.

Maps one canonical :class:`StreamDelta` into zero or more
:class:`OpenAIChatStreamChunk` wire events.  Tool-call arguments stay
raw JSON strings and source call indices are preserved verbatim; a
``finish`` delta emits a terminal chunk and a ``usage`` delta emits a
usage-only terminal chunk with an empty ``choices`` list.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.errors import stream_state_invalid
from lexigram.ai.relay.stream.state import (
    StreamSnapshot,
    _first_tool_contribution,
)
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.dto import (
    OpenAIChatStreamChoice,
    OpenAIChatStreamChunk,
    OpenAIChatStreamDelta,
)
from lexigram.contracts.ai.relay.ir import StreamDelta
from lexigram.contracts.ai.relay.types import RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = ["openai_chat_emitter"]


def _chunk(
    state: StreamSnapshot,
    choice: OpenAIChatStreamChoice,
    *,
    usage: dict[str, Any] | None = None,
) -> OpenAIChatStreamChunk:
    """Build one wire chunk stamped with the session identity."""
    return OpenAIChatStreamChunk(
        id=state.stream_id or "",
        model=state.model,
        created=state.created or 0,
        choices=[choice],
        usage=usage,
    )


def _usage_to_wire(usage: RelayUsage) -> dict[str, Any]:
    """Serialize canonical usage into the OpenAI wire usage dict."""
    data: dict[str, Any] = {
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
    }
    if usage.cache_read_tokens:
        data["prompt_tokens_details"] = {"cached_tokens": usage.cache_read_tokens}
    if usage.reasoning_tokens:
        data["completion_tokens_details"] = {"reasoning_tokens": usage.reasoning_tokens}
    if usage.audio_input_tokens or usage.audio_output_tokens:
        data["audio_tokens"] = {
            "input_tokens": usage.audio_input_tokens,
            "output_tokens": usage.audio_output_tokens,
        }
    return data


def _tool_call_fragment(
    state: StreamSnapshot, delta: StreamDelta
) -> dict[str, Any] | None:
    """Serialize one tool-call delta as a partial wire fragment.

    An id-only fragment that opens a call is deferred and merged into the
    following fragment so the call id and function name never arrive
    apart; argument fragments stay raw strings.  ``None`` means the delta
    produces no fragment on the wire.
    """
    index = delta.tool_call_index
    if index is None:
        return None
    record = next((r for r in state.tool_calls if r.index == index), None)
    first = _first_tool_contribution(state, delta)
    fragment: dict[str, Any] = {"index": index}
    if delta.tool_call_arguments is not None:
        fragment["function"] = {"arguments": delta.tool_call_arguments}
    elif delta.tool_call_name is not None:
        if delta.tool_call_id is not None:
            fragment["id"] = delta.tool_call_id
        elif record is not None and record.id:
            fragment["id"] = record.id
        fragment["function"] = {"name": delta.tool_call_name}
    elif delta.tool_call_id is not None:
        if first:
            return None
        fragment["id"] = delta.tool_call_id
    return fragment


def openai_chat_emitter(
    delta: StreamDelta, *, state: StreamSnapshot
) -> Result[tuple[OpenAIChatStreamChunk, ...], RelayError]:
    """Map one canonical delta into Chat stream chunks.

    Args:
        delta: One canonical stream delta.
        state: Accumulated session snapshot.

    Returns:
        Ok(tuple of chunks) on success; ``stream_state_invalid`` for an
        unknown delta kind.
    """
    if delta.kind == "role":
        choice = OpenAIChatStreamChoice(
            index=0,
            delta=OpenAIChatStreamDelta(role=delta.role),
        )
        return Ok((_chunk(state, choice),))
    if delta.kind == "content":
        choice = OpenAIChatStreamChoice(
            index=0,
            delta=OpenAIChatStreamDelta(content=delta.content),
        )
        return Ok((_chunk(state, choice),))
    if delta.kind == "thinking":
        choice = OpenAIChatStreamChoice(
            index=0,
            delta=OpenAIChatStreamDelta(reasoning_content=delta.thinking_delta),
        )
        return Ok((_chunk(state, choice),))
    if delta.kind == "tool_call":
        fragment = _tool_call_fragment(state, delta)
        if fragment is None:
            return Ok(())
        choice = OpenAIChatStreamChoice(
            index=0,
            delta=OpenAIChatStreamDelta(tool_calls=[fragment]),
        )
        return Ok((_chunk(state, choice),))
    if delta.kind == "finish":
        choice = OpenAIChatStreamChoice(
            index=0,
            delta=OpenAIChatStreamDelta(),
            finish_reason=delta.finish_reason,
        )
        return Ok((_chunk(state, choice),))
    if delta.kind == "usage":
        if delta.usage is None:
            return Ok(())
        chunk = OpenAIChatStreamChunk(
            id=state.stream_id or "",
            model=state.model,
            created=state.created or 0,
            choices=[],
            usage=_usage_to_wire(delta.usage),
        )
        return Ok((chunk,))
    if delta.kind == "status":
        return Ok(())
    return Err(
        stream_state_invalid(f"unknown delta kind {delta.kind!r} for openai_chat")
    )
