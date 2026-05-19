"""Tests for the relay gateway failover tracker.

Covers threshold bans through the channel registry's runtime overrides,
success-driven recovery with tracker journal semantics, and operator
drain protection.
"""

from __future__ import annotations

import pytest

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations.failover import RelayFailoverTracker
from lexigram.contracts.ai.relay import RelayChannel, RelayFormat


def registry() -> RelayChannelRegistry:
    """A registry with one channel per format."""
    return RelayChannelRegistry(
        RelayGatewayConfig(
            channels=(
                RelayChannel(
                    name="claude",
                    upstream_base_url="https://upstream.example.com/claude",
                    target_format=RelayFormat.CLAUDE,
                    models=("claude-sonnet",),
                ),
                RelayChannel(
                    name="gemini",
                    upstream_base_url="https://upstream.example.com/gemini",
                    target_format=RelayFormat.GEMINI,
                    models=("gemini-pro",),
                ),
            )
        )
    )


def tracker(reg: RelayChannelRegistry, threshold: int = 2) -> RelayFailoverTracker:
    """A tracker bound to *reg* with the given threshold."""
    return RelayFailoverTracker(registry=reg, threshold=threshold)


def test_rejects_non_positive_threshold() -> None:
    with pytest.raises(ValueError, match="positive"):
        RelayFailoverTracker(registry=registry(), threshold=0)


def test_bans_channel_at_threshold() -> None:
    reg = registry()
    t = tracker(reg)  # threshold 2
    t.record_failure("claude")
    assert t.failure_count("claude") == 1
    assert "claude" not in t.banned()
    t.record_failure("claude")
    assert "claude" in t.banned()
    assert reg.runtime_enabled() == {"claude": False}


def test_banned_channel_is_invisible_to_selection() -> None:
    reg = registry()
    t = tracker(reg)
    t.record_failure("claude")
    t.record_failure("claude")
    result = reg.select(source=RelayFormat.OPENAI_CHAT, model="claude-sonnet")
    assert result.is_err()


def test_success_restores_banned_channel() -> None:
    reg = registry()
    t = tracker(reg)
    t.record_failure("claude")
    t.record_failure("claude")
    assert "claude" in t.banned()
    t.record_success("claude")
    assert "claude" not in t.banned()
    assert t.failure_count("claude") == 0
    assert reg.runtime_enabled() == {}
    result = reg.select(source=RelayFormat.OPENAI_CHAT, model="claude-sonnet")
    assert result.is_ok()


def test_success_resets_failures_below_threshold() -> None:
    reg = registry()
    t = tracker(reg)
    t.record_failure("claude")
    assert t.failure_count("claude") == 1
    t.record_success("claude")
    assert t.failure_count("claude") == 0
    assert "claude" not in t.banned()


def test_failures_are_per_channel() -> None:
    reg = registry()
    t = tracker(reg)
    t.record_failure("claude")
    assert t.failure_count("gemini") == 0
    t.record_failure("claude")
    assert "claude" in t.banned()
    assert "gemini" not in t.banned()


def test_operator_drain_is_not_restored_by_success() -> None:
    reg = registry()
    reg.set_runtime_enabled("gemini", False)
    t = tracker(reg, threshold=5)
    t.record_success("gemini")
    assert reg.runtime_enabled() == {"gemini": False}


def test_self_ban_set_is_only_tracker_disables() -> None:
    reg = registry()
    t = tracker(reg)
    reg.set_runtime_enabled("gemini", False)
    t.record_failure("claude")
    t.record_failure("claude")
    assert t.banned() == frozenset({"claude"})
    assert reg.runtime_enabled() == {"claude": False, "gemini": False}
