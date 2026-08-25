"""Channel eligibility filtering tests for ``RelayChannelRegistry.select``.

Verifies ordering guarantees, exact-model matching, format filtering,
disabled/drain gating, and capability subsetting.
"""

from __future__ import annotations

from channel_registry_support import (
    MODEL,
    SOURCE,
    build_registry,
    make_channel,
)
from lexigram.contracts.ai.relay import RelayFormat, RelayGatewayError


class TestSelectionOrder:
    """Ordering: preferred, exact model, priority, then stable name."""

    def test_lowest_priority_number_wins(self) -> None:
        registry = build_registry(
            make_channel("a", priority=100),
            make_channel("b", priority=50),
            make_channel("c", priority=200),
        )
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_equal_priorities_use_stable_name_order(self) -> None:
        registry = build_registry(make_channel("zebra"), make_channel("mango"), make_channel("apple"))
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "apple"

    def test_preferred_channel_wins_even_when_not_top_priority(self) -> None:
        registry = build_registry(make_channel("a", priority=1), make_channel("b", priority=50))
        result = registry.select(SOURCE, MODEL, preferred="b")
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_preferred_channel_failing_filters_falls_through(self) -> None:
        registry = build_registry(
            make_channel("low", priority=1),
            make_channel("high", priority=199, models=("other-model",)),
        )
        result = registry.select(SOURCE, MODEL, preferred="high")
        assert result.is_ok()
        assert result.unwrap().name == "low"

    def test_unknown_preferred_channel_falls_through(self) -> None:
        registry = build_registry(make_channel("only"))
        result = registry.select(SOURCE, MODEL, preferred="ghost")
        assert result.is_ok()
        assert result.unwrap().name == "only"

    def test_stream_true_excludes_channel_declaring_capabilities_without_stream(self) -> None:
        registry = build_registry(
            make_channel("nostream", capabilities=frozenset({"json"}), priority=1),
            make_channel("plain", priority=2),
        )
        result = registry.select(SOURCE, MODEL, stream=True)
        assert result.is_ok()
        assert result.unwrap().name == "plain"

    def test_stream_true_keeps_channel_with_empty_capabilities(self) -> None:
        registry = build_registry(make_channel("plain"))
        result = registry.select(SOURCE, MODEL, stream=True)
        assert result.is_ok()
        assert result.unwrap().name == "plain"

    def test_stream_true_keeps_channel_declaring_stream(self) -> None:
        registry = build_registry(make_channel("streamer", capabilities=frozenset({"stream"})))
        result = registry.select(SOURCE, MODEL, stream=True)
        assert result.is_ok()
        assert result.unwrap().name == "streamer"


class TestModelMatch:
    """Exact model matching and MODEL_NOT_FOUND classification."""

    def test_exact_model_match_beats_priority_and_casing(self) -> None:
        registry = build_registry(
            make_channel("cased", models=("Claude-3-5-Sonnet",), priority=1),
            make_channel("exact", models=(MODEL,), priority=100),
        )
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "exact"

    def test_missing_model_returns_typed_error(self) -> None:
        registry = build_registry(make_channel("only"))
        result = registry.select(SOURCE, "gpt-4o")
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "MODEL_NOT_FOUND"
        assert err.status_code == 404


class TestFormatFilter:
    """A channel that would do a no-op conversion is not eligible."""

    def test_target_equal_to_source_is_not_eligible(self) -> None:
        registry = build_registry(
            make_channel("same", target_format=SOURCE, priority=1),
            make_channel("other", target_format=RelayFormat.CLAUDE, priority=100),
        )
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "other"

    def test_all_channels_same_format_as_source(self) -> None:
        registry = build_registry(
            make_channel("a", target_format=SOURCE),
            make_channel("b", target_format=SOURCE),
        )
        result = registry.select(SOURCE, MODEL)
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "TARGET_FORMAT_UNSUPPORTED"
        assert err.status_code == 500


class TestDisabled:
    """The ``enabled`` flag gates eligibility."""

    def test_all_disabled_channels_return_typed_error(self) -> None:
        registry = build_registry(make_channel("a", enabled=False), make_channel("b", enabled=False))
        result = registry.select(SOURCE, MODEL)
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "CHANNEL_DISABLED"
        assert err.status_code == 404

    def test_disabled_channel_with_exact_model_ignored(self) -> None:
        registry = build_registry(
            make_channel("disabled", enabled=False, priority=1),
            make_channel("enabled", priority=100),
        )
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "enabled"

    def test_runtime_drain_gates_new_requests(self) -> None:
        registry = build_registry(make_channel("a", priority=1), make_channel("b", priority=100))
        registry.set_runtime_enabled("a", False)
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_runtime_drain_of_last_channel_is_disabled(self) -> None:
        registry = build_registry(make_channel("a", priority=1))
        registry.set_runtime_enabled("a", False)
        result = registry.select(SOURCE, MODEL)
        assert result.is_err()
        assert result.unwrap_err().code == "CHANNEL_DISABLED"

    def test_runtime_enable_restores_selection(self) -> None:
        registry = build_registry(make_channel("a", priority=1), make_channel("b", priority=100))
        registry.set_runtime_enabled("a", False)
        registry.set_runtime_enabled("a", True)
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "a"

    def test_runtime_cannot_enable_config_disabled_channel(self) -> None:
        registry = build_registry(make_channel("off", enabled=False, priority=1))
        registry.set_runtime_enabled("off", True)
        result = registry.select(SOURCE, MODEL)
        assert result.is_err()
        assert result.unwrap_err().code == "CHANNEL_DISABLED"

    def test_runtime_state_is_readable(self) -> None:
        registry = build_registry(make_channel("a"), make_channel("b"))
        registry.set_runtime_enabled("b", False)
        assert registry.runtime_enabled() == {"b": False}


class TestCapabilities:
    """Requested capability flags must be a subset of the channel's."""

    def test_missing_capability_returns_typed_error(self) -> None:
        registry = build_registry(make_channel("only", capabilities=frozenset({"stream"})))
        result = registry.select(SOURCE, MODEL, capabilities=frozenset({"vision"}))
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "CAPABILITY_UNAVAILABLE"
        assert err.status_code == 409

    def test_no_candidate_declares_requested_capability(self) -> None:
        registry = build_registry(
            make_channel("a", capabilities=frozenset({"stream"})),
            make_channel("b", capabilities=frozenset({"json"})),
        )
        result = registry.select(SOURCE, MODEL, capabilities=frozenset({"vision"}))
        assert result.is_err()
        assert result.unwrap_err().code == "CAPABILITY_UNAVAILABLE"

    def test_requested_capabilities_subset_is_accepted(self) -> None:
        registry = build_registry(
            make_channel("rich", capabilities=frozenset({"stream", "json", "vision"})),
        )
        result = registry.select(SOURCE, MODEL, capabilities=frozenset({"json"}))
        assert result.is_ok()
        assert result.unwrap().name == "rich"

    def test_empty_requested_capabilities_are_unconstrained(self) -> None:
        registry = build_registry(make_channel("a", capabilities=frozenset({"stream"})))
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "a"
