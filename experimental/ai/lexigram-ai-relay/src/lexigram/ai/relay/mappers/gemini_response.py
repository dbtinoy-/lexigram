"""Google Gemini ``generateContent`` response conversion.

Parses :class:`GeminiResponse` wire DTOs into canonical
:class:`RelayResponse` (:func:`response_to_ir`) and rebuilds them from
canonical IR (:func:`ir_to_response`).  Stream conversion is handled by
the shared stream lifecycle task and reports ``unsupported_feature``
until then.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import translate, unsupported_format
from lexigram.ai.relay.finish_reasons import (
    FINISH_REASON_TO_WIRE,
    finish_reason_to_wire,
)
from lexigram.ai.relay.mappers.base import record_loss
from lexigram.ai.relay.mappers.gemini_request import (
    _TARGET,
    _tool_call_from_part,
    _tool_call_to_part,
)
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.llm import ToolCall
from lexigram.contracts.ai.relay.dto import (
    GeminiCandidate,
    GeminiContent,
    GeminiGroundingMetadata,
    GeminiPart,
    GeminiPromptFeedback,
    GeminiResponse,
    GeminiSafetyRating,
    GeminiUsageMetadata,
)
from lexigram.contracts.ai.relay.ir import RelayResponse, normalize_finish_reason
from lexigram.contracts.ai.relay.types import RelayUsage
from lexigram.contracts.ai.thinking import ThinkingResult
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = ["ir_to_response", "response_to_ir"]


def response_to_ir(
    payload: Any, *, context: ConversionContext
) -> Result[RelayResponse, RelayError]:
    """Convert a ``GeminiResponse`` into canonical ``RelayResponse``.

    Args:
        payload: A wire response DTO.
        context: Per-conversion context with loss sink.

    Returns:
        Ok(response) on success, Err(relay_error) on malformed payload.
    """
    if not isinstance(payload, GeminiResponse):
        return Err(
            unsupported_format(f"expected GeminiResponse, got {type(payload).__name__}")
        )
    try:
        candidates = payload.candidates or []
        if len(candidates) > 1:
            record_loss(
                context,
                field="candidates",
                target=_TARGET,
                reason="multiple_candidates_collapsed",
            )
        candidate = candidates[0] if candidates else None
        passthrough: dict[str, Any] = dict(payload.passthrough)
        if payload.model_version is not None:
            passthrough["model_version"] = payload.model_version
        if payload.create_time is not None:
            passthrough["create_time"] = payload.create_time
        if payload.prompt_feedback is not None:
            passthrough["prompt_feedback"] = payload.prompt_feedback.to_dict()
        content = ""
        thinking: ThinkingResult | None = None
        tool_calls: list[ToolCall] = []
        if candidate is not None and candidate.content is not None:
            text_parts: list[str] = []
            think_parts: list[str] = []
            think_signature: str | None = None
            for part in candidate.content.parts:
                if part.thought:
                    think_parts.append(part.text or "")
                    think_signature = part.thought_signature
                elif part.text is not None:
                    text_parts.append(part.text)
                elif part.function_call is not None:
                    tool_calls.append(_tool_call_from_part(part))
                elif part.inline_data is not None or part.function_response is not None:
                    record_loss(
                        context,
                        field="content.part",
                        target=_TARGET,
                        reason="unrepresentable_part_dropped",
                    )
            content = "".join(text_parts)
            if think_parts:
                thinking = ThinkingResult(
                    content="".join(think_parts),
                    signature=think_signature,
                    tokens=_thought_tokens(payload),
                )
            _preserve_candidate_metadata(candidate, passthrough)
        return Ok(
            RelayResponse(
                model=payload.model_version or "",
                id=payload.response_id,
                content=content,
                thinking=thinking,
                tool_calls=tool_calls,
                finish_reason=normalize_finish_reason(
                    candidate.finish_reason if candidate else None
                ),
                usage=_usage_from_wire(payload.usage_metadata),
                passthrough=passthrough,
            )
        )
    except (RelayError, ValueError, TypeError, KeyError) as exc:
        return Err(translate(exc, detail="response_to_ir"))


def ir_to_response(
    response: RelayResponse, *, context: ConversionContext
) -> Result[Any, RelayError]:
    """Convert canonical ``RelayResponse`` into a ``GeminiResponse``.

    Args:
        response: Canonical response IR.
        context: Per-conversion context with loss sink.

    Returns:
        Ok(response) on success, Err(relay_error) on failure.
    """
    try:
        passthrough = dict(response.passthrough)
        model_version = passthrough.pop("model_version", None)
        prompt_feedback = passthrough.pop("prompt_feedback", None)
        create_time = passthrough.pop("create_time", None)
        safety_ratings = passthrough.pop("safety_ratings", None)
        grounding_metadata = passthrough.pop("grounding_metadata", None)
        citation_metadata = passthrough.pop("citation_metadata", None)
        token_count = passthrough.pop("token_count", None)
        avg_logprobs = passthrough.pop("avg_logprobs", None)
        parts: list[GeminiPart] = []
        if response.content:
            parts.append(GeminiPart(text=response.content))
        for tool_call in response.tool_calls:
            parts.append(_tool_call_to_part(tool_call))
        candidate = GeminiCandidate(
            content=GeminiContent(role="model", parts=parts),
            finish_reason=_finish_reason_from_ir(response.finish_reason, context),
            index=0,
            safety_ratings=_safety_ratings_from_passthrough(safety_ratings) or [],
            grounding_metadata=_grounding_from_passthrough(grounding_metadata),
            citation_metadata=(
                citation_metadata if isinstance(citation_metadata, dict) else None
            ),
            token_count=token_count if isinstance(token_count, int) else None,
            avg_logprobs=(
                avg_logprobs if isinstance(avg_logprobs, (int, float)) else None
            ),
            passthrough=dict(passthrough),
        )
        return Ok(
            GeminiResponse(
                candidates=[candidate],
                prompt_feedback=_prompt_feedback_from_passthrough(prompt_feedback),
                usage_metadata=_usage_to_wire(response.usage),
                model_version=model_version if isinstance(model_version, str) else None,
                create_time=create_time if isinstance(create_time, str) else None,
                passthrough=passthrough,
            )
        )
    except (RelayError, ValueError, TypeError, KeyError) as exc:
        return Err(translate(exc, detail="ir_to_response"))


def _usage_from_wire(usage: GeminiUsageMetadata | None) -> RelayUsage | None:
    """Map a wire ``GeminiUsageMetadata`` into canonical ``RelayUsage``.

    Mirrors relaykit's ``UsageFromGeminiMetadata``: completion counts
    thinking tokens, the prompt adds tool-use tokens, and the explicit
    total is preserved because Gemini counts thoughts within both.
    """
    if usage is None:
        return None
    return RelayUsage(
        prompt_tokens=(usage.prompt_token_count + usage.tool_use_prompt_token_count),
        completion_tokens=(
            usage.candidates_token_count + (usage.thoughts_token_count or 0)
        ),
        cache_read_tokens=usage.cached_content_token_count or 0,
        reasoning_tokens=usage.thoughts_token_count or 0,
        total_tokens_override=usage.total_token_count or None,
    )


def _usage_to_wire(usage: RelayUsage | None) -> GeminiUsageMetadata | None:
    """Serialize canonical ``RelayUsage`` into a ``GeminiUsageMetadata``.

    Gemini reports thinking tokens as a subset of the candidate
    tokens and does not surface cache or reasoning fields in the
    generated payload, so those counters are emitted as zeros.
    """
    if usage is None:
        return None
    return GeminiUsageMetadata(
        prompt_token_count=usage.prompt_tokens,
        candidates_token_count=usage.completion_tokens,
        total_token_count=usage.total_tokens,
        cached_content_token_count=0,
        thoughts_token_count=0,
        tool_use_prompt_token_count=0,
    )


def _thought_tokens(payload: GeminiResponse) -> int | None:
    """Read thinking tokens from the usage metadata."""
    if (
        payload.usage_metadata is None
        or not payload.usage_metadata.thoughts_token_count
    ):
        return None
    return payload.usage_metadata.thoughts_token_count


def _preserve_candidate_metadata(
    candidate: GeminiCandidate, passthrough: dict[str, Any]
) -> None:
    """Preserve candidate-level provider metadata as passthrough."""
    if candidate.safety_ratings:
        passthrough["safety_ratings"] = [
            rating.to_dict() for rating in candidate.safety_ratings
        ]
    if candidate.grounding_metadata is not None:
        passthrough["grounding_metadata"] = candidate.grounding_metadata.to_dict()
    if candidate.citation_metadata is not None:
        passthrough["citation_metadata"] = candidate.citation_metadata
    if candidate.token_count is not None:
        passthrough["token_count"] = candidate.token_count
    if candidate.avg_logprobs is not None:
        passthrough["avg_logprobs"] = candidate.avg_logprobs
    passthrough.update(candidate.passthrough)


def _finish_reason_from_ir(
    finish_reason: str | None, context: ConversionContext
) -> str | None:
    """Map a canonical finish reason back to a Gemini value."""
    if finish_reason is None:
        return None
    if finish_reason == "function_call":
        record_loss(
            context,
            field="finish_reason",
            target=_TARGET,
            reason="function_call_adapted",
        )
    elif finish_reason not in FINISH_REASON_TO_WIRE:
        record_loss(
            context,
            field="finish_reason",
            target=_TARGET,
            reason="finish_reason_adapted",
        )
    return finish_reason_to_wire(finish_reason, _TARGET)


def _safety_ratings_from_passthrough(
    raw: Any,
) -> list[GeminiSafetyRating] | None:
    """Rebuild safety ratings from passthrough dicts."""
    if not isinstance(raw, list):
        return None
    ratings = [
        GeminiSafetyRating.from_dict(item) for item in raw if isinstance(item, dict)
    ]
    return ratings or None


def _grounding_from_passthrough(raw: Any) -> GeminiGroundingMetadata | None:
    """Rebuild grounding metadata from a passthrough dict."""
    if not isinstance(raw, dict):
        return None
    return GeminiGroundingMetadata.from_dict(raw)


def _prompt_feedback_from_passthrough(
    raw: Any,
) -> GeminiPromptFeedback | None:
    """Rebuild prompt feedback from a passthrough dict."""
    if not isinstance(raw, dict):
        return None
    return GeminiPromptFeedback.from_dict(raw)
