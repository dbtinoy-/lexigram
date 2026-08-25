"""Tests for relay engine response conversion and stream surface."""

from __future__ import annotations

from lexigram.ai.relay import RelayConverterEngine, RelayConverterRegistry
from lexigram.ai.relay.mappers.openai_chat import OpenAIChatMapper
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.relay.dto import GeminiResponse
from lexigram.contracts.ai.relay.types import ConversionQuality, RelayFormat

from _test_engine_support import chat_response, registry


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


def test_new_stream_session_unsupported_for_now() -> None:
    """Stream sessions report unsupported_feature until the lifecycle task."""
    engine = RelayConverterEngine(registry)
    result = engine.new_stream_session(
        RelayFormat.OPENAI_CHAT,
        RelayFormat.CLAUDE,
    )
    assert result.is_err()
    assert result.unwrap_err().code == RelayErrorCode.UNSUPPORTED_FEATURE.value
