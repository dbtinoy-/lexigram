"""Tests for the relay engine explicit-path helpers and diagnostics."""

from __future__ import annotations

from lexigram.ai.relay import (
    CONVERTER_VERSION,
    RelayConverterEngine,
    RelayConverterRegistry,
    convert_request_by_id,
    convert_request_via,
    convert_response_by_id,
    convert_response_via,
)
from lexigram.contracts.ai.exceptions import RelayErrorCode
from lexigram.contracts.ai.relay.dto import (
    ClaudeRequest,
    GeminiRequest,
    GeminiResponse,
)
from lexigram.contracts.ai.relay.types import RelayFormat
from lexigram.contracts.core.result import Result

from _test_engine_support import (
    chat_request,
    chat_response,
    registry,
    responses_request,
)


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
    assert isinstance(
        RelayConverterEngine(registry).convert_request(
            chat_request(), RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE
        ),
        Result,
    )


def test_registry_exposes_converter_diagnostics() -> None:
    """The default registry reports routes, mapper ids, and version."""
    assert registry.converter_version() == CONVERTER_VERSION
    routes = registry.converter_routes()
    assert (RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE) in routes
    assert len(routes) == 12
    assert not any(source is target for source, target in routes)
    assert registry.mapper_ids() == (
        "claude",
        "gemini",
        "openai_chat",
        "openai_responses",
    )
