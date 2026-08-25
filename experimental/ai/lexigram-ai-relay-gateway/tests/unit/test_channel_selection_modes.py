"""Selection-mode tests: exclusion, endpoint-kind selection, weighted tie-break."""

from __future__ import annotations

from channel_registry_support import (
    MODEL,
    SOURCE,
    build_registry,
    build_weighted_registry,
    make_channel,
)
from lexigram.contracts.ai.relay import RelayGatewayError


class TestSelectForEndpoint:
    """Endpoint-kind selection filters on ``endpoint_kinds`` like ``select``."""

    def test_kind_match_returns_chat_compatible_channel(self) -> None:
        registry = build_registry(
            make_channel("chat", priority=1),
            make_channel("emb", endpoint_kinds=frozenset({"embeddings"})),
        )
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "emb"

    def test_no_channel_declares_kind_is_model_not_found(self) -> None:
        registry = build_registry(make_channel("chat"))
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "MODEL_NOT_FOUND"
        assert err.status_code == 404

    def test_kind_channel_missing_model_is_model_not_found(self) -> None:
        registry = build_registry(
            make_channel("emb", endpoint_kinds=frozenset({"embeddings"}), models=("other",))
        )
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_err()
        assert result.unwrap_err().code == "MODEL_NOT_FOUND"

    def test_disabled_kind_channel_ignored(self) -> None:
        registry = build_registry(
            make_channel("off", endpoint_kinds=frozenset({"embeddings"}), enabled=False),
            make_channel("on", endpoint_kinds=frozenset({"embeddings"}), priority=100),
        )
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "on"

    def test_runtime_drain_gates_endpoint_selection(self) -> None:
        registry = build_registry(
            make_channel("emb", endpoint_kinds=frozenset({"embeddings"})),
            make_channel("backup", priority=100),
        )
        registry.set_runtime_enabled("emb", False)
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_err()
        assert result.unwrap_err().code == "MODEL_NOT_FOUND"

    def test_all_disabled_returns_channel_disabled(self) -> None:
        registry = build_registry(
            make_channel("a", endpoint_kinds=frozenset({"embeddings"}), enabled=False),
        )
        result = registry.select_for_endpoint("embeddings", MODEL)
        assert result.is_err()
        assert result.unwrap_err().code == "CHANNEL_DISABLED"

    def test_exclude_skips_named_channels(self) -> None:
        registry = build_registry(
            make_channel("a", endpoint_kinds=frozenset({"embeddings"}), priority=1),
            make_channel("b", endpoint_kinds=frozenset({"embeddings"}), priority=2),
        )
        result = registry.select_for_endpoint(
            "embeddings", MODEL, exclude=frozenset({"a"})
        )
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_exclude_all_matches_is_model_not_found(self) -> None:
        registry = build_registry(
            make_channel("a", endpoint_kinds=frozenset({"embeddings"}))
        )
        result = registry.select_for_endpoint(
            "embeddings", MODEL, exclude=frozenset({"a"})
        )
        assert result.is_err()
        assert result.unwrap_err().code == "MODEL_NOT_FOUND"

    def test_priority_then_stable_name_ordering(self) -> None:
        registry = build_registry(
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
        registry = build_registry(
            make_channel("a", priority=1),
            make_channel("b", priority=50),
        )
        result = registry.select(SOURCE, MODEL, exclude=frozenset({"a"}))
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_empty_exclude_reproduces_exact_selection(self) -> None:
        registry = build_registry(
            make_channel("a", priority=100),
            make_channel("b", priority=50),
            make_channel("c", priority=200),
        )
        default = registry.select(SOURCE, MODEL)
        explicit = registry.select(SOURCE, MODEL, exclude=frozenset())
        assert default.unwrap().name == explicit.unwrap().name == "b"

    def test_excluded_preferred_channel_is_not_preferred(self) -> None:
        registry = build_registry(
            make_channel("a", priority=1),
            make_channel("b", priority=50),
        )
        result = registry.select(SOURCE, MODEL, preferred="a", exclude=frozenset({"a"}))
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_excluding_every_eligible_channel_falls_through_filters(self) -> None:
        registry = build_registry(make_channel("only"))
        result = registry.select(SOURCE, MODEL, exclude=frozenset({"only"}))
        assert result.is_err()
        assert result.unwrap_err().code == "TARGET_FORMAT_UNSUPPORTED"

    def test_excluded_channel_skipped_before_format_filter(self) -> None:
        registry = build_registry(
            make_channel("same", target_format=SOURCE),
            make_channel("good", priority=50),
        )
        result = registry.select(SOURCE, MODEL, exclude=frozenset({"same"}))
        assert result.is_ok()
        assert result.unwrap().name == "good"


class TestWeightedSelection:
    """Weighted tie-break among equal-priority top tiers (plan H, Task 2)."""

    def test_weighted_roll_in_first_weight_picks_it(self) -> None:
        registry = build_weighted_registry((0,), make_channel("a", weight=1), make_channel("b", weight=3))
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "a"

    def test_weighted_roll_covers_multiple_weights_lands_later(self) -> None:
        registry = build_weighted_registry((3,), make_channel("a", weight=1), make_channel("b", weight=3))
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "b"

    def test_weighted_deterministic_config_channel_unchanged(self) -> None:
        registry = build_registry(make_channel("z", weight=100), make_channel("a", weight=1))
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "a"

    def test_weighted_zero_weight_excluded_unless_only_candidate(self) -> None:
        only = build_weighted_registry((0,), make_channel("zero", weight=0))
        assert only.select(SOURCE, MODEL).unwrap().name == "zero"
        with_others = build_weighted_registry((0,), make_channel("zero", weight=0), make_channel("five", weight=5))
        assert with_others.select(SOURCE, MODEL).unwrap().name == "five"

    def test_weighted_preferred_channel_wins_regardless_of_weight(self) -> None:
        registry = build_weighted_registry(
            (9,), make_channel("heavy", priority=1, weight=10), make_channel("light", weight=10)
        )
        result = registry.select(SOURCE, MODEL, preferred="light")
        assert result.is_ok()
        assert result.unwrap().name == "light"

    def test_weighted_priority_tier_beats_other_tier_weights(self) -> None:
        registry = build_weighted_registry(
            (0,),
            make_channel("tier1", priority=1, weight=1),
            make_channel("tier2", priority=100, weight=1000),
        )
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap().name == "tier1"

    def test_weighted_exclude_still_removes_from_pool(self) -> None:
        registry = build_weighted_registry(
            (0,),
            make_channel("a", weight=1000),
            make_channel("b", weight=1),
        )
        result = registry.select(SOURCE, MODEL, exclude=frozenset({"a"}))
        assert result.is_ok()
        assert result.unwrap().name == "b"
