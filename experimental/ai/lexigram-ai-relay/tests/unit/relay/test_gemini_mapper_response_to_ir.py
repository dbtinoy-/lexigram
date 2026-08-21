"""Gemini mapper tests: wire response to canonical IR (``response_to_ir``)."""

from __future__ import annotations

import pytest

from gemini_mapper_test_helpers import (
    function_call_part,
    gemini_content,
    mapper,
    text_part,
    thought_part,
)
from lexigram.ai.relay.context import ConversionContext
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.relay.dto import (
    GeminiCandidate,
    GeminiGroundingMetadata,
    GeminiPromptFeedback,
    GeminiResponse,
    GeminiSafetyRating,
    GeminiUsageMetadata,
)
from lexigram.contracts.ai.relay.types import RelayUsage


def test_response_wrong_type(ctx: ConversionContext) -> None:
    """A non-Gemini payload is an unsupported_format error."""
    from lexigram.contracts.ai.relay.dto import ClaudeResponse

    result = mapper.response_to_ir(ClaudeResponse(id="m", model="c"), context=ctx)
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value


def test_response_text(ctx: ConversionContext) -> None:
    """Candidate text maps to canonical content."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(content=gemini_content("model", text_part("Hi there")))
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == "Hi there"


def test_response_thinking_and_signature(ctx: ConversionContext) -> None:
    """Thought parts map into a ThinkingResult with signature and tokens."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(
                content=gemini_content("model", thought_part("Think.", "sig1"))
            )
        ],
        usage_metadata=GeminiUsageMetadata(
            prompt_token_count=10,
            candidates_token_count=5,
            total_token_count=15,
            thoughts_token_count=3,
        ),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.thinking is not None
    assert ir.thinking.content == "Think."
    assert ir.thinking.signature == "sig1"
    assert ir.thinking.tokens == 3


def test_response_function_call(ctx: ConversionContext) -> None:
    """A functionCall part maps to a canonical ToolCall."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(
                content=gemini_content("model", function_call_part("w", {"q": 1}))
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == ""
    assert ir.tool_calls[0].function.name == "w"
    assert ir.tool_calls[0].function.arguments == {"q": 1}


def test_response_tool_only_output(ctx: ConversionContext) -> None:
    """Tool-only output keeps content empty with tool calls populated."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(
                content=gemini_content("model", function_call_part("w", {})),
                finish_reason="STOP",
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == ""
    assert ir.tool_calls
    assert ir.finish_reason == "stop"


@pytest.mark.parametrize(
    ("wire", "expected"),
    [
        ("STOP", "stop"),
        ("MAX_TOKENS", "length"),
        ("SAFETY", "content_filter"),
        ("RECITATION", "content_filter"),
        ("MALFORMED_FUNCTION_CALL", "function_call"),
        ("OTHER", "other"),
        ("MODEL_FINISH_REASON_UNSPECIFIED", "other"),
        (None, None),
    ],
)
def test_response_finish_reasons(
    ctx: ConversionContext, wire: str | None, expected: str | None
) -> None:
    """Gemini finish reasons map to the canonical set."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(
                content=gemini_content("model", text_part("x")),
                finish_reason=wire,
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.finish_reason == expected


def test_response_multiple_candidates_collapsed(ctx: ConversionContext) -> None:
    """Extra candidates collapse into the first with a loss."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(content=gemini_content("model", text_part("first"))),
            GeminiCandidate(content=gemini_content("model", text_part("second"))),
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == "first"
    assert any(loss.reason == "multiple_candidates_collapsed" for loss in ctx.losses)


def test_response_usage_metadata(ctx: ConversionContext) -> None:
    """usageMetadata maps into RelayUsage including cached and thoughts."""
    response = GeminiResponse(
        candidates=[GeminiCandidate(content=gemini_content("model", text_part("x")))],
        usage_metadata=GeminiUsageMetadata(
            prompt_token_count=100,
            candidates_token_count=20,
            total_token_count=120,
            cached_content_token_count=30,
            thoughts_token_count=5,
        ),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.usage == RelayUsage(
        prompt_tokens=100,
        completion_tokens=25,
        cache_read_tokens=30,
        reasoning_tokens=5,
        total_tokens_override=120,
    )


def test_response_model_version_passthrough(ctx: ConversionContext) -> None:
    """modelVersion and responseId survive as passthrough/metadata."""
    response = GeminiResponse(
        candidates=[GeminiCandidate(content=gemini_content("model", text_part("x")))],
        model_version="gemini-2.5-flash-001",
        response_id="resp_1",
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.id == "resp_1"
    assert ir.passthrough["model_version"] == "gemini-2.5-flash-001"


def test_response_prompt_feedback_passthrough(ctx: ConversionContext) -> None:
    """Prompt feedback survives as passthrough."""
    response = GeminiResponse(
        candidates=[GeminiCandidate(content=gemini_content("model", text_part("x")))],
        prompt_feedback=GeminiPromptFeedback(block_reason="SAFETY"),
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.passthrough["prompt_feedback"] == {"blockReason": "SAFETY"}


def test_response_safety_and_grounding_passthrough(ctx: ConversionContext) -> None:
    """Candidate safety ratings and grounding metadata survive."""
    response = GeminiResponse(
        candidates=[
            GeminiCandidate(
                content=gemini_content("model", text_part("x")),
                safety_ratings=[
                    GeminiSafetyRating(
                        category="HARM_CATEGORY_HATE_SPEECH", probability="HIGH"
                    )
                ],
                grounding_metadata=GeminiGroundingMetadata(web_search_queries=["q"]),
            )
        ]
    )
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.passthrough["safety_ratings"] == [
        {"category": "HARM_CATEGORY_HATE_SPEECH", "probability": "HIGH"}
    ]
    assert ir.passthrough["grounding_metadata"] == {"webSearchQueries": ["q"]}


def test_response_empty(ctx: ConversionContext) -> None:
    """An empty response yields defaults."""
    response = GeminiResponse()
    ir = mapper.response_to_ir(response, context=ctx).unwrap()
    assert ir.content == ""
    assert ir.finish_reason is None
    assert ir.usage is None
