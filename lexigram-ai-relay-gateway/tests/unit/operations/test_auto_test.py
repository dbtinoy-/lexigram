"""Unit tests for the relay gateway channel auto-tester.

Covers the periodic background sweep: disabling unhealthy channels
exactly once per probe transition, re-enabling only channels this
tester itself disabled (never a human-drained channel), the
start/stop lifecycle, and loop survival when a probe raises.
"""

from __future__ import annotations

import asyncio

from structlog.testing import capture_logs

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations.auto_test import RelayChannelAutoTester
from lexigram.ai.relay.gateway.operations.health import (
    RelayChannelCheckerProtocol,
    RelayChannelProbeResult,
    RelayHealthService,
)
from lexigram.contracts.ai.relay import RelayChannel, RelayFormat

BASE_URL = "https://upstream.example.com/v1"
CREDENTIAL = "sk-relay-test-secret"

FAST_PROBE = RelayChannelProbeResult(ok=True, latency_ms=42.0)
DOWN_PROBE = RelayChannelProbeResult(
    ok=False, latency_ms=600.0, failure="upstream returned 500"
)


def make_channel(
    name: str = "claude",
    target: RelayFormat = RelayFormat.CLAUDE,
    models: tuple[str, ...] = ("haiku", "sonnet"),
    *,
    enabled: bool = True,
    timeout_seconds: float = 1.0,
) -> RelayChannel:
    """Build a channel bound to a fake upstream URL."""
    return RelayChannel(
        name=name,
        upstream_base_url=f"{BASE_URL}/{name}?api_key={CREDENTIAL}",
        target_format=target,
        models=models,
        enabled=enabled,
        timeout_seconds=timeout_seconds,
    )


def make_config(
    *channels: RelayChannel,
) -> RelayGatewayConfig:
    """Build a gateway config around the given channels."""
    return RelayGatewayConfig(channels=channels)


class StubChecker(RelayChannelCheckerProtocol):
    """Checker returning per-channel probe results.

    A ``None`` value (or a missing key) means the checker has no signal
    for the channel, which the service reports as ``unavailable``.
    """

    def __init__(
        self,
        results: dict[str, RelayChannelProbeResult | None],
    ) -> None:
        self.results = results
        self.check_calls: list[str] = []

    async def check(self, channel: RelayChannel) -> RelayChannelProbeResult | None:
        self.check_calls.append(channel.name)
        return self.results.get(channel.name)


class ExplodingChecker(RelayChannelCheckerProtocol):
    """Checker raising on its first probe, then returning healthy."""

    def __init__(self) -> None:
        self.exploded = False

    async def check(self, channel: RelayChannel) -> RelayChannelProbeResult | None:
        if not self.exploded:
            self.exploded = True
            raise RuntimeError("probe exploded")
        return FAST_PROBE


class RecordingRegistry(RelayChannelRegistry):
    """A registry journaling every runtime transition it applied."""

    def __init__(self, config: RelayGatewayConfig) -> None:
        super().__init__(config)
        self.transitions: list[tuple[str, bool]] = []

    def set_runtime_enabled(self, channel: str, enabled: bool) -> None:
        self.transitions.append((channel, enabled))
        super().set_runtime_enabled(channel, enabled)


def make_tester(
    *channels: RelayChannel,
    results: dict[str, RelayChannelProbeResult | None],
    interval_seconds: float = 600.0,
) -> tuple[RelayChannelAutoTester, RecordingRegistry, StubChecker]:
    """Build a tester bound to a recording registry and stubbed checker."""
    registry = RecordingRegistry(make_config(*channels))
    checker = StubChecker(results)
    health = RelayHealthService(registry=registry, checker=checker)
    tester = RelayChannelAutoTester(
        health=health,
        registry=registry,
        interval_seconds=interval_seconds,
    )
    return tester, registry, checker


async def test_sweep_disables_failed_channels_once_per_state_change() -> None:
    """A failed channel is disabled exactly once, not on every sweep."""
    tester, registry, _ = make_tester(
        make_channel("claude", target=RelayFormat.CLAUDE),
        make_channel("openai", target=RelayFormat.OPENAI_CHAT),
        results={"claude": FAST_PROBE, "openai": DOWN_PROBE},
    )
    await tester.sweep()
    await tester.sweep()
    assert registry.transitions == [("openai", False)]
    assert registry.runtime_enabled() == {"openai": False}


async def test_recovered_channel_is_reenabled_by_this_tester() -> None:
    """A channel that probes healthy again is restored at runtime."""
    tester, registry, checker = make_tester(
        make_channel(name="claude"),
        results={"claude": DOWN_PROBE},
    )
    await tester.sweep()
    assert registry.runtime_enabled() == {"claude": False}
    checker.results = {"claude": FAST_PROBE}
    await tester.sweep()
    assert registry.runtime_enabled() == {}
    assert registry.transitions == [("claude", False), ("claude", True)]


async def test_human_drained_channel_is_not_reenabled() -> None:
    """A channel drained through the controls path stays drained."""
    tester, registry, _ = make_tester(
        make_channel(name="claude"),
        results={"claude": FAST_PROBE},
    )
    registry.set_runtime_enabled("claude", False)
    await tester.sweep()
    assert registry.transitions == [("claude", False)]
    assert registry.runtime_enabled() == {"claude": False}


async def test_start_schedules_loop_and_stop_cancels_cleanly() -> None:
    """``start()`` runs sweeps on the interval; ``stop()`` halts them."""
    tester, registry, checker = make_tester(
        make_channel(name="claude"),
        results={"claude": DOWN_PROBE},
        interval_seconds=0.02,
    )
    await tester.start()
    assert tester.is_running
    for _ in range(50):
        if registry.transitions:
            break
        await asyncio.sleep(0.01)
    assert registry.transitions == [("claude", False)]
    await tester.stop()
    assert not tester.is_running
    seen = len(checker.check_calls)
    await asyncio.sleep(0.05)
    assert len(checker.check_calls) == seen


async def test_start_twice_is_a_noop() -> None:
    """A second ``start()`` while running does not spawn a second loop."""
    tester, registry, _ = make_tester(
        make_channel(name="claude"),
        results={"claude": DOWN_PROBE},
        interval_seconds=600.0,
    )
    await tester.start()
    await tester.start()
    assert registry.transitions == []
    await tester.stop()
    assert not tester.is_running


async def test_probe_exception_does_not_stop_the_loop() -> None:
    """A raising probe is logged and the next sweep still runs."""
    registry = RecordingRegistry(make_config(make_channel(name="claude")))
    health = RelayHealthService(
        registry=registry,
        checker=ExplodingChecker(),
    )
    tester = RelayChannelAutoTester(
        health=health,
        registry=registry,
        interval_seconds=0.02,
    )
    with capture_logs() as logs:
        await tester.start()
        for _ in range(50):
            if "relay_gateway_channel_auto_sweep_failed" in {
                entry["event"] for entry in logs
            }:
                break
            await asyncio.sleep(0.01)
        await tester.stop()
    names = [entry["event"] for entry in logs]
    assert "relay_gateway_channel_auto_sweep_failed" in names


async def test_stop_before_start_is_clean() -> None:
    """Stopping a tester that never started raises nothing."""
    tester, _, _ = make_tester(
        make_channel(name="claude"),
        results={"claude": FAST_PROBE},
    )
    await tester.stop()
    assert not tester.is_running