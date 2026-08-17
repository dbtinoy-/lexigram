"""Round-trip invariants for every directed route.

Task 13 Step 3: text, tool names, tool argument JSON, usage totals, and
explicit zero/false values must survive a full source -> target ->
source round trip wherever the target protocol can represent them.

The forward hop of every route is pinned to the relaykit goldens by
:mod:`test_golden_matrix`; this test pins the *round trip itself* so a
future change cannot lose information that all four target protocols can
carry.  Where the relaykit mappers intentionally drop data on a hop
(e.g. ``max_output_tokens`` on ``openai_responses -> openai_chat``), the
golden fixtures stay authoritative and no loss is asserted.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay import RelayConverterRegistry
from lexigram.ai.relay.engine import convert_request_by_id, convert_response_by_id
from lexigram.contracts.ai.relay.context import RelayConversionContext

from ._fixtures import FORMAT_SLUGS, REQUEST_FIXTURES, RESPONSE_FIXTURES, routes
from .conftest import REQUEST_DTOS, RESPONSE_DTOS

SOURCE_PROMPT = {"openai": 10, "openai_responses": 10, "claude": 10, "gemini": 10}
SOURCE_COMPLETION = {"openai": 5, "openai_responses": 5, "claude": 5, "gemini": 7}

# The recorded relaykit goldens render gemini -> claude request bodies with
# empty user ``content`` (the multimodal payload is dropped on that hop), so
# a round trip containing that hop cannot preserve the user's text.  All
# other routes preserve it.
GEMINI_TO_CLAUDE_TEXT_ROUTES = {
    "gemini_to_claude",
    "claude_to_gemini",
}


def _string_leaves(value: Any) -> list[str]:
    """Flatten a wire tree into its string leaves (keys included)."""
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            out.append(str(key))
            out.extend(_string_leaves(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(_string_leaves(item))
        return out
    return [str(value)]


def _contains(dto: dict[str, Any], marker: str) -> bool:
    return any(marker in leaf for leaf in _string_leaves(dto))


def _round_trip_request(
    registry: RelayConverterRegistry,
    route: str,
    ctx: RelayConversionContext,
) -> dict[str, Any]:
    """Convert the request fixture source->target->source and serialize back."""
    source_slug, target_slug = route.split("_to_", 1)
    source = FORMAT_SLUGS[source_slug]
    target = FORMAT_SLUGS[target_slug]
    forward = convert_request_by_id(
        registry,
        REQUEST_DTOS[source_slug].from_dict(REQUEST_FIXTURES[source_slug]),
        f"{source}_to_{target}",
        context=ctx,
    )
    assert forward.is_ok(), forward.unwrap_err()
    target_dto = forward.unwrap().value
    backward = convert_request_by_id(
        registry,
        REQUEST_DTOS[target_slug].from_dict(target_dto.to_dict()),
        f"{target}_to_{source}",
        context=ctx,
    )
    assert backward.is_ok(), backward.unwrap_err()
    return backward.unwrap().value.to_dict()


def _round_trip_response(
    registry: RelayConverterRegistry,
    route: str,
    ctx: RelayConversionContext,
) -> tuple[dict[str, Any], Any]:
    """Round-trip a response fixture; return its wire dict and final usage."""
    source_slug, target_slug = route.split("_to_", 1)
    source = FORMAT_SLUGS[source_slug]
    target = FORMAT_SLUGS[target_slug]
    forward = convert_response_by_id(
        registry,
        RESPONSE_DTOS[source_slug].from_dict(RESPONSE_FIXTURES[source_slug]),
        f"{source}_to_{target}",
        context=ctx,
    )
    assert forward.is_ok(), forward.unwrap_err()
    target_dto = forward.unwrap().value
    backward = convert_response_by_id(
        registry,
        RESPONSE_DTOS[target_slug].from_dict(target_dto.to_dict()),
        f"{target}_to_{source}",
        context=ctx,
    )
    assert backward.is_ok(), backward.unwrap_err()
    outcome = backward.unwrap()
    return outcome.value.to_dict(), outcome.usage


@pytest.mark.parametrize("route", routes("request"))
def test_request_text_and_tool_invariants_survive(
    route: str, registry: RelayConverterRegistry, ctx: RelayConversionContext
) -> None:
    """User text, tool names, and tool arguments survive every round trip."""
    result = _round_trip_request(registry, route, ctx)
    assert _contains(result, "get_weather")
    assert _contains(result, "Paris")
    if route not in GEMINI_TO_CLAUDE_TEXT_ROUTES:
        assert _contains(result, "What is in this image?")


@pytest.mark.parametrize("route", routes("response"))
def test_response_text_and_tool_invariants_survive(
    route: str, registry: RelayConverterRegistry, ctx: RelayConversionContext
) -> None:
    """Generated text, tool names, and tool arguments survive round trips."""
    result, _ = _round_trip_response(registry, route, ctx)
    assert _contains(result, "The answer is 42.")
    assert _contains(result, "get_weather")
    assert _contains(result, "Paris")


@pytest.mark.parametrize("route", routes("response"))
def test_response_usage_totals_never_shrink(
    route: str, registry: RelayConverterRegistry, ctx: RelayConversionContext
) -> None:
    """Prompt and completion totals never lose source token counts."""
    source_slug, _ = route.split("_to_", 1)
    _, usage = _round_trip_response(registry, route, ctx)
    assert usage is not None
    assert usage.prompt_tokens >= SOURCE_PROMPT[source_slug]
    assert usage.completion_tokens >= SOURCE_COMPLETION[source_slug]


def test_request_explicit_zero_values_survive(
    registry: RelayConverterRegistry, ctx: RelayConversionContext
) -> None:
    """Explicit zero temperature/top_p survive openai -> claude -> openai."""
    forward = convert_request_by_id(
        registry,
        REQUEST_DTOS["openai"].from_dict(
            {
                "model": "gpt-test",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1024,
                "temperature": 0.0,
                "top_p": 0,
            }
        ),
        "openai_chat_to_claude",
        context=ctx,
    )
    assert forward.is_ok(), forward.unwrap_err()
    backward = convert_request_by_id(
        registry,
        REQUEST_DTOS["claude"].from_dict(forward.unwrap().value.to_dict()),
        "claude_to_openai_chat",
        context=ctx,
    )
    assert backward.is_ok(), backward.unwrap_err()
    result = backward.unwrap().value.to_dict()
    assert result["temperature"] == 0.0
    assert result["top_p"] == 0
