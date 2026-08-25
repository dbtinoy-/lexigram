"""Tests for relay engine request conversion scenarios."""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay import RelayConverterEngine, RelayConverterRegistry
from lexigram.ai.relay.mappers.claude import ClaudeMapper
from lexigram.ai.relay.mappers.openai_chat import OpenAIChatMapper
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.relay.context import RelayConversionContext
from lexigram.contracts.ai.relay.dto import ClaudeRequest
from lexigram.contracts.ai.relay.types import (
    ConversionQuality,
    RelayFormat,
    RelayLoss,
)

from _test_engine_support import chat_request, registry


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
