"""Deterministic channel selection tests (Relay Gateway plan, Task 2).

Verifies the ordering guarantees, filtering, error classification, and
config validation of ``RelayChannelRegistry.select``.
"""

from __future__ import annotations

import pytest

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.contracts.ai.relay import RelayChannel, RelayFormat, RelayGatewayError

SOURCE = RelayFormat.OPENAI_CHAT
MODEL = "claude-3-5-sonnet"


def make_channel(name: str = "a", **overrides: object) -> RelayChannel:
    """Build a channel with sensible defaults; ``overrides`` win."""
    defaults: dict[str, object] = {
        "name": name,
        "upstream_base_url": "https://upstream-a/v1",
        "target_format": RelayFormat.CLAUDE,
        "models": (MODEL,),
        "capabilities": frozenset(),
        "priority": 100,
        "enabled": True,
        "timeout_seconds": 60.0,
    }
    defaults.update(overrides)
    return RelayChannel(**defaults)  # type: ignore[arg-type]


def _registry(*channels: RelayChannel) -> RelayChannelRegistry:
    """Build a registry over the given channels."""
    return RelayChannelRegistry(RelayGatewayConfig(channels=channels))


def _weighted(roll: int, *channels: RelayChannel) -> RelayChannelRegistry:
    """Build a weighted-mode registry whose random source always returns ``roll``."""
    config = RelayGatewayConfig(channels=channels, load_balancing="weighted")
    return RelayChannelRegistry(config, random_source=lambda _: roll)


class TestSelectionOrder:
    """Ordering: preferred, exact model, priority, then stable name."""

    def test_lowest_priority_number_wins(self) -> None:
        registry = _registry(
            make_channel("a", priority=100),
            make_channel("b", priority=50),
            make_channel("c", priority=200),
        )
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_equal_priorities_use_stable_name_order(self) -> None:
        registry = _registry(make_channel("zebra"), make_channel("mango"), make_channel("apple"))
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "apple"

    def test_preferred_channel_wins_even_when_not_top_priority(self) -> None:
        registry = _registry(make_channel("a", priority=1), make_channel("b", priority=50))
        result = registry.select(SOURCE, MODEL, preferred="b")
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_preferred_channel_failing_filters_falls_through(self) -> None:
        registry = _registry(
            make_channel("low", priority=1),
            make_channel("high", priority=199, models=("other-model",)),
        )
        result = registry.select(SOURCE, MODEL, preferred="high")
        assert result.is_ok()
        assert result.unwrap().name == "low"

    def test_unknown_preferred_channel_falls_through(self) -> None:
        registry = _registry(make_channel("only"))
        result = registry.select(SOURCE, MODEL, preferred="ghost")
        assert result.is_ok()
        assert result.unwrap().name == "only"

    def test_stream_true_excludes_channel_declaring_capabilities_without_stream(self) -> None:
        registry = _registry(
            make_channel("nostream", capabilities=frozenset({"json"}), priority=1),
            make_channel("plain", priority=2),
        )
        result = registry.select(SOURCE, MODEL, stream=True)
        assert result.is_ok()
        assert result.unwrap().name == "plain"

    def test_stream_true_keeps_channel_with_empty_capabilities(self) -> None:
        registry = _registry(make_channel("plain"))
        result = registry.select(SOURCE, MODEL, stream=True)
        assert result.is_ok()
        assert result.unwrap().name == "plain"

    def test_stream_true_keeps_channel_declaring_stream(self) -> None:
        registry = _registry(make_channel("streamer", capabilities=frozenset({"stream"})))
        result = registry.select(SOURCE, MODEL, stream=True)
        assert result.is_ok()
        assert result.unwrap().name == "streamer"


class TestModelMatch:
    """Exact model matching and MODEL_NOT_FOUND classification."""

    def test_exact_model_match_beats_priority_and_casing(self) -> None:
        registry = _registry(
            make_channel("cased", models=("Claude-3-5-Sonnet",), priority=1),
            make_channel("exact", models=(MODEL,), priority=100),
        )
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "exact"

    def test_missing_model_returns_typed_error(self) -> None:
        registry = _registry(make_channel("only"))
        result = registry.select(SOURCE, "gpt-4o")
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "MODEL_NOT_FOUND"
        assert err.status_code == 404


class TestFormatFilter:
    """A channel that would do a no-op conversion is not eligible."""

    def test_target_equal_to_source_is_not_eligible(self) -> None:
        registry = _registry(
            make_channel("same", target_format=SOURCE, priority=1),
            make_channel("other", target_format=RelayFormat.CLAUDE, priority=100),
        )
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "other"

    def test_all_channels_same_format_as_source(self) -> None:
        registry = _registry(
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
        registry = _registry(make_channel("a", enabled=False), make_channel("b", enabled=False))
        result = registry.select(SOURCE, MODEL)
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "CHANNEL_DISABLED"
        assert err.status_code == 404

    def test_disabled_channel_with_exact_model_ignored(self) -> None:
        registry = _registry(
            make_channel("disabled", enabled=False, priority=1),
            make_channel("enabled", priority=100),
        )
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "enabled"

    def test_runtime_drain_gates_new_requests(self) -> None:
        registry = _registry(make_channel("a", priority=1), make_channel("b", priority=100))
        registry.set_runtime_enabled("a", False)
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_runtime_drain_of_last_channel_is_disabled(self) -> None:
        registry = _registry(make_channel("a", priority=1))
        registry.set_runtime_enabled("a", False)
        result = registry.select(SOURCE, MODEL)
        assert result.is_err()
        assert result.unwrap_err().code == "CHANNEL_DISABLED"

    def test_runtime_enable_restores_selection(self) -> None:
        registry = _registry(make_channel("a", priority=1), make_channel("b", priority=100))
        registry.set_runtime_enabled("a", False)
        registry.set_runtime_enabled("a", True)
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "a"

    def test_runtime_cannot_enable_config_disabled_channel(self) -> None:
        registry = _registry(make_channel("off", enabled=False, priority=1))
        registry.set_runtime_enabled("off", True)
        result = registry.select(SOURCE, MODEL)
        assert result.is_err()
        assert result.unwrap_err().code == "CHANNEL_DISABLED"

    def test_runtime_state_is_readable(self) -> None:
        registry = _registry(make_channel("a"), make_channel("b"))
        registry.set_runtime_enabled("b", False)
        assert registry.runtime_enabled() == {"b": False}


class TestCapabilities:
    """Requested capability flags must be a subset of the channel's."""

    def test_missing_capability_returns_typed_error(self) -> None:
        registry = _registry(make_channel("only", capabilities=frozenset({"stream"})))
        result = registry.select(SOURCE, MODEL, capabilities=frozenset({"vision"}))
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "CAPABILITY_UNAVAILABLE"
        assert err.status_code == 409

    def test_no_candidate_declares_requested_capability(self) -> None:
        registry = _registry(
            make_channel("a", capabilities=frozenset({"stream"})),
            make_channel("b", capabilities=frozenset({"json"})),
        )
        result = registry.select(SOURCE, MODEL, capabilities=frozenset({"vision"}))
        assert result.is_err()
        assert result.unwrap_err().code == "CAPABILITY_UNAVAILABLE"

    def test_requested_capabilities_subset_is_accepted(self) -> None:
        registry = _registry(
            make_channel("rich", capabilities=frozenset({"stream", "json", "vision"})),
        )
        result = registry.select(SOURCE, MODEL, capabilities=frozenset({"json"}))
        assert result.is_ok()
        assert result.unwrap().name == "rich"

    def test_empty_requested_capabilities_are_unconstrained(self) -> None:
        registry = _registry(make_channel("a", capabilities=frozenset({"stream"})))
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "a"


class TestCopySemantics:
    """Selection returns the configured channel without mutating config."""

    def test_selected_channel_is_frozen_and_equals_config_channel(self) -> None:
        channels = (make_channel("a"), make_channel("b"))
        config = RelayGatewayConfig(channels=channels)
        registry = RelayChannelRegistry(config)
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        selected = result.unwrap()
        assert isinstance(selected, RelayChannel)
        assert selected == channels[0]
        assert config.channels == channels

    def test_config_channels_never_reordered(self) -> None:
        channels = (
            make_channel("z", priority=1),
            make_channel("y", priority=2),
            make_channel("x", priority=3),
        )
        config = RelayGatewayConfig(channels=channels)
        registry = RelayChannelRegistry(config)
        first = registry.select(SOURCE, MODEL)
        second = registry.select(SOURCE, MODEL, preferred="x")
        assert first.is_ok()
        assert second.is_ok()
        assert first.unwrap().name == "z"
        assert second.unwrap().name == "x"
        assert config.channels == channels


class TestConfigValidation:
    """RelayGatewayConfig rejects duplicate channel names and bad auto-test config."""

    def test_duplicate_channel_names_raise(self) -> None:
        with pytest.raises(ValueError):
            RelayGatewayConfig(channels=(make_channel("dup"), make_channel("dup")))

    def test_empty_config_is_valid(self) -> None:
        config = RelayGatewayConfig()
        assert config.channels == ()
        assert config.model_suffix == {}
        assert config.provider_options == {}
        assert config.auto_test_channels is False
        assert config.auto_test_interval_seconds == 600

    def test_auto_test_fields_roundtrip(self) -> None:
        config = RelayGatewayConfig(
            channels=(make_channel("a"),),
            auto_test_channels=True,
            auto_test_interval_seconds=30,
        )
        assert config.auto_test_channels is True
        assert config.auto_test_interval_seconds == 30

    def test_zero_auto_test_interval_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            RelayGatewayConfig(auto_test_interval_seconds=0)

    def test_negative_auto_test_interval_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            RelayGatewayConfig(channels=(make_channel("a"),), auto_test_interval_seconds=-1)

    def test_max_upstream_retries_defaults_to_zero(self) -> None:
        config = RelayGatewayConfig()
        assert config.max_upstream_retries == 0

    def test_max_upstream_retries_roundtrip(self) -> None:
        config = RelayGatewayConfig(
            channels=(make_channel("a"),),
            max_upstream_retries=2,
        )
        assert config.max_upstream_retries == 2

    def test_negative_max_upstream_retries_raises(self) -> None:
        with pytest.raises(ValueError, match="retries"):
            RelayGatewayConfig(max_upstream_retries=-1)


class TestSelectForEndpoint:
    """Endpoint-kind selection filters on ``endpoint_kinds`` like ``select``."""

    def test_kind_match_returns_chat_compatible_channel(self) -> None:
        registry = _registry(
            make_channel("chat", priority=1),
            make_channel("emb", endpoint_kinds=frozenset({"embeddings"})),
        )
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "emb"

    def test_no_channel_declares_kind_is_model_not_found(self) -> None:
        registry = _registry(make_channel("chat"))
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "MODEL_NOT_FOUND"
        assert err.status_code == 404

    def test_kind_channel_missing_model_is_model_not_found(self) -> None:
        registry = _registry(
            make_channel("emb", endpoint_kinds=frozenset({"embeddings"}), models=("other",))
        )
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_err()
        assert result.unwrap_err().code == "MODEL_NOT_FOUND"

    def test_disabled_kind_channel_ignored(self) -> None:
        registry = _registry(
            make_channel("off", endpoint_kinds=frozenset({"embeddings"}), enabled=False),
            make_channel("on", endpoint_kinds=frozenset({"embeddings"}), priority=100),
        )
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "on"

    def test_runtime_drain_gates_endpoint_selection(self) -> None:
        registry = _registry(
            make_channel("emb", endpoint_kinds=frozenset({"embeddings"})),
            make_channel("backup", priority=100),
        )
        registry.set_runtime_enabled("emb", False)
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_err()
        assert result.unwrap_err().code == "MODEL_NOT_FOUND"

    def test_all_disabled_returns_channel_disabled(self) -> None:
        registry = _registry(
            make_channel("a", endpoint_kinds=frozenset({"embeddings"}), enabled=False),
        )
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_err()
        assert result.unwrap_err().code == "CHANNEL_DISABLED"

    def test_exclude_skips_named_channels(self) -> None:
        registry = _registry(
            make_channel("a", endpoint_kinds=frozenset({"embeddings"}), priority=1),
            make_channel("b", endpoint_kinds=frozenset({"embeddings"}), priority=2),
        )
        result = registry.select_for_endpoint(
            "embeddings", MODEL, exclude=frozenset({"a"})
        )
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_exclude_all_matches_is_model_not_found(self) -> None:
        registry = _registry(
            make_channel("a", endpoint_kinds=frozenset({"embeddings"}))
        )
        result = registry.select_for_endpoint(
            "embeddings", MODEL, exclude=frozenset({"a"})
        )
        assert result.is_err()
        assert result.unwrap_err().code == "MODEL_NOT_FOUND"

    def test_priority_then_stable_name_ordering(self) -> None:
        registry = _registry(
            make_channel("z", endpoint_kinds=frozenset({"embeddings"}), priority=100),
            make_channel("a", endpoint_kinds=frozenset({"embeddings"}), priority=100),
            make_channel("b", endpoint_kinds=frozenset({"embeddings"}), priority=50),
        )
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "b"


class TestSelectExclude:
    """Exclusion filtering on ``select`` for failover retries."""

    def test_excluded_channel_is_never_the_top_pick(self) -> None:
        registry = _registry(
            make_channel("a", priority=1),
            make_channel("b", priority=50),
        )
        result = registry.select(SOURCE, MODEL, exclude=frozenset({"a"}))
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_empty_exclude_reproduces_exact_selection(self) -> None:
        registry = _registry(
            make_channel("a", priority=100),
            make_channel("b", priority=50),
            make_channel("c", priority=200),
        )
        default = registry.select(SOURCE, MODEL)
        explicit = registry.select(SOURCE, MODEL, exclude=frozenset())
        assert default.unwrap().name == explicit.unwrap().name == "b"

    def test_excluded_preferred_channel_is_not_preferred(self) -> None:
        registry = _registry(
            make_channel("a", priority=1),
            make_channel("b", priority=50),
        )
        result = registry.select(SOURCE, MODEL, preferred="a", exclude=frozenset({"a"}))
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_excluding_every_eligible_channel_falls_through_filters(self) -> None:
        registry = _registry(make_channel("only"))
        result = registry.select(SOURCE, MODEL, exclude=frozenset({"only"}))
        assert result.is_err()
        assert result.unwrap_err().code == "TARGET_FORMAT_UNSUPPORTED"

    def test_excluded_channel_skipped_before_format_filter(self) -> None:
        registry = _registry(
            make_channel("same", target_format=SOURCE),
            make_channel("good", priority=50),
        )
        result = registry.select(SOURCE, MODEL, exclude=frozenset({"same"}))
        assert result.is_ok()
        assert result.unwrap().name == "good"


class TestProviderOptionsAndSuffix:
    """model_suffix / provider_options round-trip and never affect selection."""

    def test_fields_roundtrip_and_selection_ignores_them(self) -> None:
        channels = (make_channel("a"),)
        config = RelayGatewayConfig(
            channels=channels,
            model_suffix={"a": ":thinking"},
            provider_options={"a": {"max_tokens": 8192}},
        )
        assert config.model_suffix == {"a": ":thinking"}
        assert config.provider_options == {"a": {"max_tokens": 8192}}
        registry = RelayChannelRegistry(config)
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap() == channels[0]


def _weighted_registry(weight_rolls: tuple[int, ...], *channels: RelayChannel) -> RelayChannelRegistry:
    """Build a weighted-mode registry with a scripted random source.

    Args:
        weight_rolls: Values the scripted random source returns in order;
            exhausted calls get 0.
        channels: Channels to configure (all share SOURCE/MODEL defaults).
    """
    config = RelayGatewayConfig(channels=channels, load_balancing="weighted")
    source = _ScriptedRandom(*weight_rolls)
    return RelayChannelRegistry(config, random_source=source)


class _ScriptedRandom:
    """A random source returning preloaded values in sequence (0 when exhausted)."""

    def __init__(self, *values: int) -> None:
        self._values = list(values)

    def __call__(self, max_value: int) -> int:
        value = self._values.pop(0) if self._values else 0
        if value >= max_value:
            return max_value - 1
        return value


class TestWeightedSelection:
    """Weighted tie-break among equal-priority top tiers (plan H, Task 2)."""

    def test_weighted_roll_in_first_weight_picks_it(self) -> None:
        registry = _weighted_registry((0,), make_channel("a", weight=1), make_channel("b", weight=3))
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "a"

    def test_weighted_roll_covers_multiple_weights_lands_later(self) -> None:
        registry = _weighted_registry((3,), make_channel("a", weight=1), make_channel("b", weight=3))
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_weighted_deterministic_config_channel_unchanged(self) -> None:
        registry = _registry(make_channel("z", weight=100), make_channel("a", weight=1))
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "a"

    def test_weighted_zero_weight_excluded_unless_only_candidate(self) -> None:
        only = _weighted_registry((0,), make_channel("zero", weight=0))
        assert only.select(SOURCE, MODEL).unwrap().name == "zero"
        with_others = _weighted_registry((0,), make_channel("zero", weight=0), make_channel("five", weight=5))
        assert with_others.select(SOURCE, MODEL).unwrap().name == "five"

    def test_weighted_preferred_channel_wins_regardless_of_weight(self) -> None:
        registry = _weighted_registry(
            (9,), make_channel("heavy", priority=1, weight=10), make_channel("light", weight=10)
        )
        result = registry.select(SOURCE, MODEL, preferred="light")
        assert result.is_ok()
        assert result.unwrap().name == "light"

    def test_weighted_priority_tier_beats_other_tier_weights(self) -> None:
        registry = _weighted_registry(
            (0,),
            make_channel("tier1", priority=1, weight=1),
            make_channel("tier2", priority=100, weight=1000),
        )
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "tier1"

    def test_weighted_exclude_still_removes_from_pool(self) -> None:
        registry = _weighted_registry(
            (0,),
            make_channel("a", weight=1000),
            make_channel("b", weight=1),
        )
        result = registry.select(SOURCE, MODEL, exclude=frozenset({"a"}))
        assert result.is_ok()
        assert result.unwrap().name == "b"
