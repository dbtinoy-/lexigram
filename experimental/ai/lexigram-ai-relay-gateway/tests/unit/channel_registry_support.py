"""Shared builders for ``RelayChannelRegistry`` unit tests.

Provides deterministic channel/config factories so every selection-behavior
test module constructs registries identically.
"""

from __future__ import annotations

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.contracts.ai.relay import RelayChannel, RelayFormat

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


def build_registry(*channels: RelayChannel) -> RelayChannelRegistry:
    """Build a registry over the given channels."""
    return RelayChannelRegistry(RelayGatewayConfig(channels=channels))


def build_weighted_registry(
    weight_rolls: tuple[int, ...], *channels: RelayChannel,
) -> RelayChannelRegistry:
    """Build a weighted-mode registry with a scripted random source.

    Args:
        weight_rolls: Values the scripted random source returns in order;
            exhausted calls get 0.
        channels: Channels to configure (all share SOURCE/MODEL defaults).
    """
    config = RelayGatewayConfig(channels=channels, load_balancing="weighted")
    source = ScriptedRandom(*weight_rolls)
    return RelayChannelRegistry(config, random_source=source)


class ScriptedRandom:
    """A random source returning preloaded values in sequence (0 when exhausted)."""

    def __init__(self, *values: int) -> None:
        self._values = list(values)

    def __call__(self, max_value: int) -> int:
        value = self._values.pop(0) if self._values else 0
        if value >= max_value:
            return max_value - 1
        return value
