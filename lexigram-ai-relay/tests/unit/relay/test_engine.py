"""Tests for the relay registry, route metadata, and conversion engine."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay import (
    RelayConverterEngine,
    RelayConverterRegistry,
    RouteSpec,
    convert_request_by_id,
    convert_request_via,
    convert_response_by_id,
    convert_response_via,
    route_quality,
)
from lexigram.ai.relay.mappers.claude import ClaudeMapper
from lexigram.ai.relay.mappers.openai_chat import OpenAIChatMapper
from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode
from lexigram.contracts.ai.relay.context import RelayConversionContext
from lexigram.contracts.ai.relay.dto import (
    ClaudeRequest,
    GeminiRequest,
    GeminiResponse,
    OpenAIChatChoice,
    OpenAIChatMessage,
    OpenAIChatRequest,
    OpenAIChatResponse,
    ResponsesRequest,
)
from lexigram.contracts.ai.relay.types import (
    ConversionQuality,
    RelayFormat,
    RelayLoss,
)
from lexigram.contracts.core.result import Result

registry = RelayConverterRegistry.with_defaults()

ALL_PAIRS: list[tuple[RelayFormat, RelayFormat]] = [
    (source, target)
    for source in RelayFormat
    for target in RelayFormat
    if source is not target
]


def chat_request(**kwargs: Any) -> OpenAIChatRequest:
    """Build a Chat request with sensible defaults."""
    defaults: dict[str, Any] = {
        "model": "gpt-4o",
        "messages": [
            OpenAIChatMessage(role="user", content="Hello"),
        ],
    }
    defaults.update(kwargs)
    return OpenAIChatRequest(**defaults)


def chat_response(**kwargs: Any) -> OpenAIChatResponse:
    """Build a Chat response with sensible defaults."""
    defaults: dict[str, Any] = {
        "id": "chat_1",
        "model": "gpt-4o",
        "object": "chat.completion",
        "created": 1700000000,
        "choices": [
            OpenAIChatChoice(
                index=0,
                message=OpenAIChatMessage(role="assistant", content="Hello"),
                finish_reason="stop",
            )
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }
    defaults.update(kwargs)
    return OpenAIChatResponse(**defaults)


def responses_request(**kwargs: Any) -> ResponsesRequest:
    """Build a Responses request with sensible defaults."""
    defaults: dict[str, Any] = {"model": "gpt-4o", "input": []}
    defaults.update(kwargs)
    return ResponsesRequest(**defaults)


# ---------------------------------------------------------------------------
# Registry construction and route metadata
# ---------------------------------------------------------------------------


def test_with_defaults_registers_all_directed_routes() -> None:
    """Every directed pair resolves a route; same-format pairs are no-ops."""
    for source in RelayFormat:
        assert registry.mapper(source, source) is None
    for source, target in ALL_PAIRS:
        assert registry.mapper(source, target) is not None


def test_with_defaults_route_specs_cover_twelve_pairs() -> None:
    """The registry exposes exactly twelve directed route specs."""
    specs = registry.routes()
    assert len(specs) == 12
    assert len({spec.converter_id for spec in specs}) == 12


def test_route_spec_carries_static_metadata() -> None:
    """Route specs carry source, target, quality, and capability flags."""
    spec = registry.route(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE)
    assert isinstance(spec, RouteSpec)
    assert spec.source is RelayFormat.OPENAI_CHAT
    assert spec.target is RelayFormat.CLAUDE
    assert spec.converter_id == "openai_chat_to_claude"
    assert spec.quality is ConversionQuality.FAIR
    assert spec.request_supported is True
    assert spec.response_supported is True
    assert spec.stream_supported is False


def test_route_quality_matches_matrix() -> None:
    """Quality per directed pair follows the plan's matrix."""
    expectations: dict[tuple[RelayFormat, RelayFormat], ConversionQuality] = {
        (RelayFormat.OPENAI_CHAT, RelayFormat.OPENAI_RESPONSES): ConversionQuality.GOOD,
        (RelayFormat.OPENAI_RESPONSES, RelayFormat.OPENAI_CHAT): ConversionQuality.GOOD,
        (RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE): ConversionQuality.FAIR,
        (RelayFormat.OPENAI_CHAT, RelayFormat.GEMINI): ConversionQuality.FAIR,
        (RelayFormat.OPENAI_RESPONSES, RelayFormat.CLAUDE): ConversionQuality.FAIR,
        (RelayFormat.OPENAI_RESPONSES, RelayFormat.GEMINI): ConversionQuality.FAIR,
        (RelayFormat.CLAUDE, RelayFormat.OPENAI_CHAT): ConversionQuality.FAIR,
        (RelayFormat.CLAUDE, RelayFormat.OPENAI_RESPONSES): ConversionQuality.FAIR,
        (RelayFormat.GEMINI, RelayFormat.OPENAI_CHAT): ConversionQuality.FAIR,
        (RelayFormat.GEMINI, RelayFormat.OPENAI_RESPONSES): ConversionQuality.FAIR,
        (RelayFormat.CLAUDE, RelayFormat.GEMINI): ConversionQuality.DISCOURAGED,
        (RelayFormat.GEMINI, RelayFormat.CLAUDE): ConversionQuality.DISCOURAGED,
    }
    for pair, expected in expectations.items():
        assert route_quality(*pair) is expected
        assert registry.route(*pair).quality is expected
    assert route_quality(RelayFormat.CLAUDE, RelayFormat.CLAUDE) is ConversionQuality.GOOD


def test_duplicate_registration_rejected() -> None:
    """Registering two mappers for one format raises a typed error."""
    registry_local = RelayConverterRegistry()
    registry_local.register(OpenAIChatMapper())
    with pytest.raises(RelayError) as exc_info:
        registry_local.register(OpenAIChatMapper())
    assert exc_info.value.code == RelayErrorCode.DUPLICATE_REGISTRATION.value


def test_register_rejects_mapper_without_format() -> None:
    """A mapper without a RelayFormat format attribute is rejected."""
    registry_local = RelayConverterRegistry()

    class NoFormat:
        pass

    with pytest.raises(RelayError) as exc_info:
        registry_local.register(NoFormat())  # type: ignore[arg-type]
    assert exc_info.value.code == RelayErrorCode.UNSUPPORTED_FORMAT.value


def test_custom_mapper_isolated_to_caller_registry() -> None:
    """A custom mapper registered on a caller registry does not leak."""
    defaults = RelayConverterRegistry.with_defaults()
    caller = RelayConverterRegistry()

    class CustomChatMapper(OpenAIChatMapper):
        pass

    caller.register(CustomChatMapper())
    caller.register(ClaudeMapper())

    custom_route = caller.mapper(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE)
    default_route = defaults.mapper(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE)
    assert isinstance(custom_route.source_mapper, CustomChatMapper)
    assert not isinstance(default_route.source_mapper, CustomChatMapper)


def test_route_by_id_lookup() -> None:
    """Routes resolve by their stable converter id."""
    spec = registry.route_by_id("openai_chat_to_claude")
    assert spec is not None
    assert (spec.source, spec.target) == (RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE)
    assert registry.route_by_id("nope_to_never") is None


# ---------------------------------------------------------------------------
# Engine — request conversion
# ---------------------------------------------------------------------------


def test_convert_request_openai_chat_to_claude() -> None:
    """A Chat request converts to a Claude request with full metadata."""
    engine = RelayConverterEngine(registry)
    result = engine.convert_request(
        chat_request(max_tokens=64),
        RelayFormat.OPENAI_CHAT,
        RelayFormat.CLAUDE,
    )
    assert result.is_ok()
    converted = result.unwrap()
    assert isinstance(converted.value, ClaudeRequest)
    assert converted.value.model == "gpt-4o"
    assert converted.value.max_tokens == 64
    assert converted.source is RelayFormat.OPENAI_CHAT
    assert converted.target is RelayFormat.CLAUDE
    assert converted.converter_id == "openai_chat_to_claude"
    assert converted.quality is ConversionQuality.FAIR
    assert converted.steps == ("openai_chat", "canonical_ir", "claude")
    assert converted.usage is None


def test_convert_request_same_format_returns_original_object() -> None:
    """Same-format conversion returns the original payload, not a copy."""
    engine = RelayConverterEngine(registry)
    payload = chat_request()
    result = engine.convert_request(
        payload,
        RelayFormat.OPENAI_CHAT,
        RelayFormat.OPENAI_CHAT,
    )
    assert result.is_ok()
    converted = result.unwrap()
    assert converted.value is payload
    assert converted.quality is ConversionQuality.GOOD
    assert converted.converter_id == "openai_chat_to_openai_chat"
    assert converted.steps == ()


def test_convert_request_unsupported_route() -> None:
    """A missing mapper for a route yields an unsupported_route error."""
    partial = RelayConverterRegistry()
    partial.register(OpenAIChatMapper())
    engine = RelayConverterEngine(partial)
    result = engine.convert_request(
        chat_request(),
        RelayFormat.OPENAI_CHAT,
        RelayFormat.CLAUDE,
    )
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_ROUTE.value


def test_convert_request_invalid_source() -> None:
    """A non-format source is rejected with unsupported_format."""
    engine = RelayConverterEngine(registry)
    result = engine.convert_request(chat_request(), "chat", RelayFormat.CLAUDE)  # type: ignore[arg-type]
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value


def test_convert_request_invalid_target() -> None:
    """A non-format target is rejected with unsupported_format."""
    engine = RelayConverterEngine(registry)
    result = engine.convert_request(chat_request(), RelayFormat.OPENAI_CHAT, "claude")  # type: ignore[arg-type]
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FORMAT.value


def test_convert_request_unexpected_exception_translated() -> None:
    """Unexpected mapper exceptions become Err results, not raises."""
    partial = RelayConverterRegistry()

    class ExplodingChatMapper(OpenAIChatMapper):
        def request_to_ir(self, payload: Any, *, context: Any = None) -> Any:
            raise RuntimeError("boom")

    partial.register(ExplodingChatMapper())
    partial.register(ClaudeMapper())
    engine = RelayConverterEngine(partial)
    result = engine.convert_request(
        chat_request(max_tokens=64),
        RelayFormat.OPENAI_CHAT,
        RelayFormat.CLAUDE,
    )
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.SERIALIZATION_ERROR.value


def test_convert_request_value_error_translated_as_malformed() -> None:
    """ValueError failures inside a mapper become malformed_payload."""
    partial = RelayConverterRegistry()

    class StrictChatMapper(OpenAIChatMapper):
        def request_to_ir(self, payload: Any, *, context: Any = None) -> Any:
            raise ValueError("bad field")

    partial.register(StrictChatMapper())
    partial.register(ClaudeMapper())
    engine = RelayConverterEngine(partial)
    result = engine.convert_request(
        chat_request(max_tokens=64),
        RelayFormat.OPENAI_CHAT,
        RelayFormat.CLAUDE,
    )
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.MALFORMED_PAYLOAD.value


def test_convert_request_records_mapper_losses() -> None:
    """Losses recorded by mappers surface on the conversion result."""
    engine = RelayConverterEngine(registry)
    request = chat_request(
        max_tokens=64,
        tools=[{"type": "web_search", "name": "web"}],
    )
    result = engine.convert_request(
        request,
        RelayFormat.OPENAI_CHAT,
        RelayFormat.CLAUDE,
    )
    assert result.is_ok()
    converted = result.unwrap()
    reasons = [loss.reason for loss in converted.losses]
    assert "non_function_tool_dropped" in reasons
    assert any("non_function_tool_dropped" in warning for warning in converted.warnings)


def test_convert_request_context_losses_flow_through() -> None:
    """Host-provided losses survive the conversion context wrap."""
    engine = RelayConverterEngine(registry)
    context = RelayConversionContext(
        losses=[
            RelayLoss(
                field="host_note",
                target=RelayFormat.CLAUDE,
                reason="host_side_loss",
                severity="info",
            )
        ]
    )
    result = engine.convert_request(
        chat_request(max_tokens=64),
        RelayFormat.OPENAI_CHAT,
        RelayFormat.CLAUDE,
        context=context,
    )
    assert result.is_ok()
    converted = result.unwrap()
    assert any(loss.reason == "host_side_loss" for loss in converted.losses)


def test_convert_request_per_call_registry_override() -> None:
    """A per-call registry override takes precedence over the engine's."""
    partial = RelayConverterRegistry()
    partial.register(OpenAIChatMapper())
    engine = RelayConverterEngine(registry)
    result = engine.convert_request(
        chat_request(),
        RelayFormat.OPENAI_CHAT,
        RelayFormat.CLAUDE,
        registry=partial,
    )
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_ROUTE.value


# ---------------------------------------------------------------------------
# Engine — response conversion
# ---------------------------------------------------------------------------


def test_convert_response_openai_chat_to_gemini() -> None:
    """A Chat response converts to a Gemini response with normalized usage."""
    engine = RelayConverterEngine(registry)
    result = engine.convert_response(
        chat_response(),
        RelayFormat.OPENAI_CHAT,
        RelayFormat.GEMINI,
    )
    assert result.is_ok()
    converted = result.unwrap()
    assert isinstance(converted.value, GeminiResponse)
    assert converted.converter_id == "openai_chat_to_gemini"
    assert converted.quality is ConversionQuality.FAIR
    assert converted.steps == ("openai_chat", "canonical_ir", "gemini")
    assert converted.usage is not None
    assert converted.usage.prompt_tokens == 10
    assert converted.usage.completion_tokens == 5
    assert converted.usage.total_tokens == 15


def test_convert_response_same_format_returns_original_object() -> None:
    """Same-format response conversion is a no-op over the original object."""
    engine = RelayConverterEngine(registry)
    payload = chat_response()
    result = engine.convert_response(
        payload,
        RelayFormat.OPENAI_CHAT,
        RelayFormat.OPENAI_CHAT,
    )
    assert result.is_ok()
    converted = result.unwrap()
    assert converted.value is payload
    assert converted.usage is None


def test_convert_response_unsupported_route() -> None:
    """A missing route yields unsupported_route for responses too."""
    partial = RelayConverterRegistry()
    partial.register(OpenAIChatMapper())
    engine = RelayConverterEngine(partial)
    result = engine.convert_response(
        chat_response(),
        RelayFormat.OPENAI_CHAT,
        RelayFormat.GEMINI,
    )
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_ROUTE.value


# ---------------------------------------------------------------------------
# Engine — stream surface
# ---------------------------------------------------------------------------


def test_new_stream_session_unsupported_for_now() -> None:
    """Stream sessions report unsupported_feature until the lifecycle task."""
    engine = RelayConverterEngine(registry)
    result = engine.new_stream_session(
        RelayFormat.OPENAI_CHAT,
        RelayFormat.CLAUDE,
    )
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FEATURE.value


# ---------------------------------------------------------------------------
# Explicit-path helpers
# ---------------------------------------------------------------------------


def test_convert_request_via() -> None:
    """convert_request_via converts through the given registry."""
    result = convert_request_via(
        registry,
        responses_request(),
        RelayFormat.OPENAI_RESPONSES,
        RelayFormat.GEMINI,
    )
    assert result.is_ok()
    assert isinstance(result.unwrap().value, GeminiRequest)


def test_convert_response_via() -> None:
    """convert_response_via converts responses through the given registry."""
    result = convert_response_via(
        registry,
        chat_response(),
        RelayFormat.OPENAI_CHAT,
        RelayFormat.GEMINI,
    )
    assert result.is_ok()
    assert isinstance(result.unwrap().value, GeminiResponse)


def test_convert_request_by_id() -> None:
    """convert_request_by_id resolves the route from its converter id."""
    result = convert_request_by_id(
        registry,
        chat_request(max_tokens=64),
        "openai_chat_to_claude",
    )
    assert result.is_ok()
    converted = result.unwrap()
    assert isinstance(converted.value, ClaudeRequest)
    assert converted.converter_id == "openai_chat_to_claude"


def test_convert_response_by_id() -> None:
    """convert_response_by_id resolves the route from its converter id."""
    result = convert_response_by_id(
        registry,
        chat_response(),
        "openai_chat_to_gemini",
    )
    assert result.is_ok()
    assert isinstance(result.unwrap().value, GeminiResponse)


def test_convert_request_by_id_unknown_route() -> None:
    """An unknown converter id yields unsupported_route."""
    result = convert_request_by_id(
        registry,
        chat_request(),
        "nope_to_never",
    )
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_ROUTE.value


def test_convert_response_by_id_unknown_route() -> None:
    """An unknown converter id yields unsupported_route for responses."""
    result = convert_response_by_id(
        registry,
        chat_response(),
        "nope_to_never",
    )
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_ROUTE.value


def test_engine_is_converter_protocol() -> None:
    """The engine satisfies the container-facing converter protocol."""
    from lexigram.contracts.ai.relay.protocols import RelayConverterProtocol

    assert isinstance(RelayConverterEngine(registry), RelayConverterProtocol)
    assert isinstance(registry, RelayConverterRegistry)
    assert isinstance(RelayConverterEngine(registry).convert_request(chat_request(), RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE), Result)