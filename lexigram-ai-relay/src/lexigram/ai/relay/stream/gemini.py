"""Google Gemini ``generateContent`` target stream emitter.

Maps one canonical :class:`StreamDelta` into zero or more
:class:`GeminiResponse` stream chunks.  Thinking parts carry the
``thought`` flag and optional ``thoughtSignature``; tool calls are
emitted as ``functionCall`` parts on the terminal chunk, where the full
accumulated argument JSON can be parsed into the target's object args.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.errors import stream_state_invalid
from lexigram.ai.relay.finish_reasons import (
    finish_reason_to_wire,
    normalize_finish_reason,
)
from lexigram.ai.relay.stream.state import StreamSnapshot
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.dto import (
    GeminiCandidate,
    GeminiContent,
    GeminiPart,
    GeminiResponse,
    GeminiUsageMetadata,
)
from lexigram.contracts.ai.relay.ir import StreamDelta
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.serialization import loads_str

__all__ = ["gemini_emitter"]


def _gemini_finish_reason(reason: str) -> str:
    """Map a canonical finish reason onto Gemini's wire values."""
    return finish_reason_to_wire(normalize_finish_reason(reason), RelayFormat.GEMINI)


def _usage_to_wire(usage: RelayUsage) -> GeminiUsageMetadata:
    """Serialize canonical usage into the Gemini usage shape."""
    return GeminiUsageMetadata(
        prompt_token_count=usage.prompt_tokens,
        candidates_token_count=usage.completion_tokens,
        total_token_count=usage.total_tokens,
        cached_content_token_count=usage.cache_read_tokens or None,
        thoughts_token_count=usage.reasoning_tokens or None,
    )


def _chunk(
    state: StreamSnapshot,
    *,
    parts: list[GeminiPart] | None = None,
    finish_reason: str | None = None,
    usage: GeminiUsageMetadata | None = None,
) -> GeminiResponse:
    """Build one wire chunk with a single candidate at index zero."""
    candidate = GeminiCandidate(
        content=GeminiContent(role="model", parts=parts or []),
        finish_reason=finish_reason,
        index=0,
    )
    return GeminiResponse(
        candidates=[candidate],
        usage_metadata=usage,
        response_id=state.stream_id,
    )


def _usage_chunk(state: StreamSnapshot, *, usage: RelayUsage) -> GeminiResponse:
    """Build a usage-only chunk carrying just usage metadata."""
    return GeminiResponse(
        candidates=[],
        usage_metadata=_usage_to_wire(usage),
        response_id=state.stream_id,
    )


def _function_call_parts(state: StreamSnapshot) -> list[GeminiPart]:
    """Build ``functionCall`` parts from the accumulated tool calls."""
    parts: list[GeminiPart] = []
    for record in state.tool_calls:
        args: dict[str, Any]
        try:
            parsed = loads_str(record.arguments)
            args = parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            args = {}
        parts.append(
            GeminiPart(
                function_call={"name": record.name, "args": args},
            )
        )
    return parts


def gemini_emitter(
    delta: StreamDelta, *, state: StreamSnapshot
) -> Result[tuple[GeminiResponse, ...], RelayError]:
    """Map one canonical delta into Gemini stream chunks.

    Args:
        delta: One canonical stream delta.
        state: Accumulated session snapshot.

    Returns:
        Ok(tuple of chunks) on success; ``stream_state_invalid`` for an
        unknown delta kind.
    """
    if delta.kind == "role":
        return Ok(())
    if delta.kind == "content":
        if not delta.content:
            return Ok(())
        return Ok((_chunk(state, parts=[GeminiPart(text=delta.content)]),))
    if delta.kind == "thinking":
        if not delta.thinking_delta:
            return Ok(())
        signature = delta.passthrough.get("signature")
        thought_signature = (
            signature if isinstance(signature, str) and signature else None
        )
        return Ok(
            (
                _chunk(
                    state,
                    parts=[
                        GeminiPart(
                            text=delta.thinking_delta,
                            thought=True,
                            thought_signature=thought_signature,
                        )
                    ],
                ),
            )
        )
    if delta.kind == "tool_call":
        return Ok(())
    if delta.kind == "finish":
        parts = _function_call_parts(state)
        finish_reason = _gemini_finish_reason(delta.finish_reason or "stop")
        usage = _usage_to_wire(state.usage) if state.usage is not None else None
        return Ok(
            (_chunk(state, parts=parts, finish_reason=finish_reason, usage=usage),)
        )
    if delta.kind == "usage":
        if state.finish_reason is not None or delta.usage is None:
            return Ok(())
        return Ok((_usage_chunk(state, usage=delta.usage),))
    if delta.kind == "status":
        return Ok(())
    return Err(stream_state_invalid(f"unknown delta kind {delta.kind!r} for gemini"))
