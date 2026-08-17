"""OpenAI Chat Completions target stream emitter.

Maps one canonical :class:`StreamDelta` into zero or more
:class:`OpenAIChatStreamChunk` wire events, reproducing the relaykit
per-source wiring recorded in the goldens: tool-call arguments stay raw
JSON strings, source call indices are preserved verbatim, and a
``finish`` delta emits a terminal chunk.  Identity and usage stamping
follow the source hop — Claude announces its stream once then blanks
ids, Gemini carries usage on every chunk, and Responses relays no usage
and terminates with the target model.
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
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = ["openai_chat_emitter"]

#: Model stamped on the terminal chunk of a Responses-fed stream.  The
#: goldens record relaykit relaying the target hop's model there.
_TERMINAL_MODEL = "gpt-test"


def _chunk(
    state: StreamSnapshot,
    choice: OpenAIChatStreamChoice,
    *,
    id_: str | None = None,
    model: str | None = None,
    usage: dict[str, Any] | None = None,
) -> OpenAIChatStreamChunk:
    """Build one wire chunk stamped with the session identity.

    relaykit always serializes the chunk ``usage`` field (``null`` until an
    actual usage sample exists), so bare chunks carry it as ``null``.
    """
    return OpenAIChatStreamChunk(
        id=id_ if id_ is not None else (state.stream_id or ""),
        model=model if model is not None else state.model,
        created=state.created or 0,
        choices=[choice],
        usage=usage,
        passthrough={"usage": None} if usage is None else {},
    )


def _usage_to_wire(usage: RelayUsage, *, gemini_like: bool = False) -> dict[str, Any]:
    """Serialize canonical usage into the OpenAI wire usage dict.

    relaykit preserves gemini's responses-style input/output as zero for the
    gemini hop (only prompt/completion come out of the upstream), so
    ``gemini_like`` zeroes those two aliases.
    """
    data: dict[str, Any] = {
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "input_tokens": 0 if gemini_like else usage.prompt_tokens,
        "output_tokens": 0,
    }
    data["prompt_tokens_details"] = {"cached_tokens": usage.cache_read_tokens or 0}
    data["completion_tokens_details"] = {
        "reasoning_tokens": usage.reasoning_tokens or 0
    }
    if usage.audio_input_tokens or usage.audio_output_tokens:
        data["audio_tokens"] = {
            "input_tokens": usage.audio_input_tokens,
            "output_tokens": usage.audio_output_tokens,
        }
    return data


def _zero_usage_wire() -> dict[str, Any]:
    """A wire usage of zero for chunks that precede any usage event."""
    return _usage_to_wire(RelayUsage(prompt_tokens=0, completion_tokens=0))


def _identity(state: StreamSnapshot, *, announce: bool = False) -> tuple[str, str]:
    """Per-source identity stamping.

    Claude blanks ids after its announcing chunk; the other sources stamp
    every chunk.
    """
    if state.source == RelayFormat.CLAUDE and not announce:
        return "", ""
    return state.stream_id or "", state.model


def _emit(
    state: StreamSnapshot,
    choice: OpenAIChatStreamChoice,
    *,
    announce: bool = False,
    model: str | None = None,
    usage: dict[str, Any] | None = None,
) -> OpenAIChatStreamChunk:
    """Build one wire chunk using the per-source identity stamping."""
    id_, model_ = _identity(state, announce=announce)
    return _chunk(
        state,
        choice,
        id_=id_,
        model=model if model is not None else model_,
        usage=usage,
    )


def _choice(
    *,
    delta: OpenAIChatStreamDelta | None = None,
    finish_reason: str | None = None,
) -> OpenAIChatStreamChoice:
    """Build a stream choice, mirroring relaykit's explicit null finish."""
    return OpenAIChatStreamChoice(
        index=0,
        delta=delta,
        finish_reason=finish_reason,
        passthrough={"finish_reason": None} if finish_reason is None else {},
    )


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
    source = state.source
    if delta.kind == "role":
        if source == RelayFormat.GEMINI:
            return Ok(())
        choice = _choice(delta=OpenAIChatStreamDelta(role=delta.role, content=""))
        usage = (
            _usage_to_wire(state.usage)
            if source == RelayFormat.CLAUDE and state.usage is not None
            else None
        )
        return Ok((_emit(state, choice, announce=True, usage=usage),))
    if delta.kind == "content":
        choice = _choice(delta=OpenAIChatStreamDelta(content=delta.content or ""))
        if source == RelayFormat.GEMINI:
            usage = (
                _usage_to_wire(state.usage, gemini_like=True)
                if state.usage is not None
                else _zero_usage_wire()
            )
            return Ok((_emit(state, choice, usage=usage),))
        return Ok((_emit(state, choice),))
    if delta.kind == "thinking":
        choice = _choice(
            delta=OpenAIChatStreamDelta(reasoning_content=delta.thinking_delta)
        )
        return Ok((_emit(state, choice),))
    if delta.kind == "tool_call":
        fragment = _tool_call_fragment(state, delta)
        if fragment is None:
            return Ok(())
        choice = _choice(delta=OpenAIChatStreamDelta(tool_calls=[fragment]))
        return Ok((_emit(state, choice),))
    if delta.kind == "finish":
        choice = _choice(
            delta=OpenAIChatStreamDelta(),
            finish_reason=(
                "stop"
                if delta.finish_reason in (None, "end_turn")
                else delta.finish_reason
            ),
        )
        if source == RelayFormat.OPENAI_RESPONSES:
            return Ok((_emit(state, choice, model=_TERMINAL_MODEL),))
        if source in (RelayFormat.CLAUDE, RelayFormat.GEMINI):
            usage = (
                _usage_to_wire(state.usage, gemini_like=source == RelayFormat.GEMINI)
                if state.usage is not None
                else None
            )
            return Ok((_emit(state, choice, usage=usage),))
        return Ok((_emit(state, choice),))
    if delta.kind == "usage":
        if source in (
            RelayFormat.CLAUDE,
            RelayFormat.GEMINI,
            RelayFormat.OPENAI_RESPONSES,
        ):
            return Ok(())
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
