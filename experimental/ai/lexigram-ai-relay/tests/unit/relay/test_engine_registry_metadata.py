"""Tests for relay converter registry construction and route metadata."""

from __future__ import annotations

import pytest

from lexigram.ai.relay import (
    RelayConverterRegistry,
    RouteSpec,
    route_quality,
)
from lexigram.ai.relay.mappers.claude import ClaudeMapper
from lexigram.ai.relay.mappers.openai_chat import OpenAIChatMapper
from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode
from lexigram.contracts.ai.relay.types import ConversionQuality, RelayFormat

from _test_engine_support import ALL_PAIRS, registry


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
    assert (
        route_quality(RelayFormat.CLAUDE, RelayFormat.CLAUDE) is ConversionQuality.GOOD
    )


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
