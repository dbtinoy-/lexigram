"""Unit tests for the relay gateway health aggregation service.

Covers ``RelayHealthService`` status mapping, bounded upstream probes,
capability diagnostics, and redaction guarantees.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
import time

import pytest

from lexigram.ai.relay.gateway import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations.health import (
    RelayChannelCheckerProtocol,
    RelayChannelProbeResult,
    RelayHealthService,
)
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    RelayChannel,
    RelayFormat,
    RelayGatewayError,
    RelayPolicySnapshot,
    RelayPolicyStoreProtocol,
    RelayRegistryDiagnostics,
    RelayRegistryProtocol,
)

BASE_URL = "https://upstream.example.com/v1"
CREDENTIAL = "sk-relay-test-secret"

FAST_PROBE = RelayChannelProbeResult(ok=True, latency_ms=42.0)
SLOW_PROBE = RelayChannelProbeResult(ok=True, latency_ms=950.0)
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
    """Checker that returns per-channel probe results.

    A ``None`` value (or a missing key) means the checker has no signal
    for the channel, which the service reports as ``unavailable``.
    """

    def __init__(
        self,
        results: dict[str, RelayChannelProbeResult | None],
    ) -> None:
        self.results = results

    async def check(self, channel: RelayChannel) -> RelayChannelProbeResult | None:
        return self.results.get(channel.name)


class HangingChecker(RelayChannelCheckerProtocol):
    """Checker that never completes; used to exercise the timeout bound."""

    async def check(self, channel: RelayChannel) -> RelayChannelProbeResult | None:
        await asyncio.sleep(60)
        return FAST_PROBE


class StaticPolicyStore(RelayPolicyStoreProtocol):
    """Policy store serving a fixed snapshot."""

    def __init__(self, snapshot: RelayPolicySnapshot) -> None:
        self.snapshot = snapshot

    async def load(self) -> RelayPolicySnapshot:
        return self.snapshot

    async def save(self, snapshot: RelayPolicySnapshot) -> None:
        self.snapshot = snapshot


class FakeRegistry(RelayRegistryProtocol):
    """Stub registry exposing routed, mappers, and version diagnostics."""

    def mapper(self, source: RelayFormat, target: RelayFormat) -> None:
        """Return a mapper for the pair, always ``None`` in this stub."""
        return

    def converter_routes(self) -> tuple[tuple[RelayFormat, RelayFormat], ...]:
        """Return the supported directed route pairs."""
        return (
            (RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE),
            (RelayFormat.CLAUDE, RelayFormat.GEMINI),
        )

    def mapper_ids(self) -> tuple[str, ...]:
        """Return registered mapper wire-format identifiers."""
        return ("claude", "gemini", "openai_chat")

    def converter_version(self) -> str:
        """Return the fixed converter version."""
        return "1.0.0"

    def route_quality(
        self,
        source: RelayFormat,
        target: RelayFormat,
    ) -> ConversionQuality:
        """Return the matrix quality for the pair."""
        return ConversionQuality.FAIR


def make_service(
    *channels: RelayChannel,
    checker: RelayChannelCheckerProtocol | None = None,
    converter: RelayRegistryProtocol | None = None,
    policy: RelayPolicyStoreProtocol | None = None,
) -> RelayHealthService:
    """Build a health service over the given channels."""
    registry = RelayChannelRegistry(make_config(*channels))
    return RelayHealthService(
        registry=registry,
        checker=checker,
        converter=converter,
        policy=policy,
    )


class TestChannelHealth:
    async def test_healthy_channel_reports_healthy(self) -> None:
        service = make_service(
            make_channel(),
            checker=StubChecker({"claude": FAST_PROBE}),
        )
        health = await service.channel_health()
        assert len(health) == 1
        entry = health[0]
        assert entry.channel == "claude"
        assert entry.status == "healthy"
        assert entry.model_count == 2
        assert entry.latency_ms_p50 == 42.0
        assert entry.latency_ms_p95 == 42.0
        assert entry.failure_count == 0
        assert entry.detail_code is None

    async def test_status_precedence(self) -> None:
        service = make_service(
            make_channel(name="fast", models=("a",)),
            make_channel(name="slow", models=("a",)),
            make_channel(name="down", models=("a",)),
            make_channel(name="unreachable", models=("a",)),
            checker=StubChecker(
                {
                    "fast": FAST_PROBE,
                    "slow": SLOW_PROBE,
                    "down": DOWN_PROBE,
                    "unreachable": None,
                }
            ),
        )
        by_name = {h.channel: h for h in await service.channel_health()}
        assert by_name["fast"].status == "healthy"
        assert by_name["slow"].status == "degraded"
        assert by_name["down"].status == "failed"
        assert by_name["down"].failure_count == 1
        assert by_name["unreachable"].status == "unavailable"

    async def test_failed_probe_takes_precedence_over_slow(self) -> None:
        service = make_service(
            make_channel(name="down", models=("a",)),
            checker=StubChecker({"down": DOWN_PROBE}),
        )
        (entry,) = await service.channel_health()
        assert entry.status == "failed"
        assert entry.detail_code == "probe_failed"

    async def test_probe_timeout_is_bounded(self) -> None:
        service = make_service(
            make_channel(timeout_seconds=0.01),
            checker=HangingChecker(),
        )
        started = time.monotonic()
        (entry,) = await service.channel_health()
        elapsed = time.monotonic() - started
        assert entry.status == "failed"
        assert entry.detail_code == "probe_timeout"
        assert entry.failure_count == 1
        assert elapsed < 5.0

    async def test_disabled_channel_is_unavailable_but_model_counted(self) -> None:
        service = make_service(
            make_channel(
                name="drained",
                models=("sonnet",),
                enabled=False,
            ),
            checker=StubChecker({"drained": FAST_PROBE}),
        )
        (entry,) = await service.channel_health()
        assert entry.status == "unavailable"
        assert entry.detail_code == "channel_disabled"
        assert entry.model_count == 1

    async def test_missing_checker_is_unavailable_everywhere(self) -> None:
        service = make_service(make_channel())
        (entry,) = await service.channel_health()
        assert entry.status == "unavailable"
        assert entry.detail_code == "dependency_missing"

    async def test_unconfigured_checker_target_is_unavailable(self) -> None:
        service = make_service(make_channel(), checker=StubChecker({}))
        (entry,) = await service.channel_health()
        assert entry.status == "unavailable"
        assert entry.detail_code == "no_probe_result"

    async def test_no_credentials_or_urls_in_output(self) -> None:
        service = make_service(
            make_channel(),
            checker=StubChecker({"claude": DOWN_PROBE}),
        )
        rendered = str(await service.channel_health())
        assert BASE_URL not in rendered
        assert CREDENTIAL not in rendered
        assert "api_key" not in rendered

    async def test_checked_at_is_utc_aware(self) -> None:
        service = make_service(
            make_channel(),
            checker=StubChecker({"claude": FAST_PROBE}),
        )
        (entry,) = await service.channel_health()
        assert entry.checked_at.tzinfo is not None
        assert entry.checked_at.utcoffset() == timedelta(0)

    async def test_runtime_drained_channel_is_unavailable(self) -> None:
        policy = StaticPolicyStore(
            RelayPolicySnapshot(
                enabled_channels={"claude": False},
                allowed_model_options={"claude": frozenset({"sonnet"})},
                media_allowed_schemes=frozenset(),
                media_allowed_hosts=frozenset(),
                max_request_bytes=1,
                max_stream_seconds=1.0,
            )
        )
        service = make_service(
            make_channel(),
            checker=StubChecker({"claude": FAST_PROBE}),
            policy=policy,
        )
        (entry,) = await service.channel_health()
        assert entry.status == "unavailable"
        assert entry.detail_code == "drained"

    async def test_configured_disabled_channel_wins_over_drain(self) -> None:
        policy = StaticPolicyStore(
            RelayPolicySnapshot(
                enabled_channels={"off": False},
                allowed_model_options={"off": frozenset({"sonnet"})},
                media_allowed_schemes=frozenset(),
                media_allowed_hosts=frozenset(),
                max_request_bytes=1,
                max_stream_seconds=1.0,
            )
        )
        service = make_service(
            make_channel(name="off", models=("sonnet",), enabled=False),
            checker=StubChecker({"off": FAST_PROBE}),
            policy=policy,
        )
        (entry,) = await service.channel_health()
        assert entry.detail_code == "channel_disabled"


class TestRegistryDiagnostics:
    async def test_reports_capabilities_from_registry(self) -> None:
        service = make_service(
            make_channel(),
            converter=FakeRegistry(),
        )
        diagnostics = await service.registry_diagnostics()
        assert isinstance(diagnostics, RelayRegistryDiagnostics)
        assert diagnostics.converter_id == "relay-converter"
        assert diagnostics.converter_version == "1.0.0"
        assert diagnostics.mapper_ids == (
            "claude",
            "gemini",
            "openai_chat",
        )
        assert (RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE) in (
            diagnostics.supported_routes
        )

    async def test_missing_converter_is_failed_dependency(self) -> None:
        service = make_service(make_channel(), converter=None)
        with pytest.raises(RelayGatewayError) as exc_info:
            await service.registry_diagnostics()
        assert exc_info.value.code == "DEPENDENCY_UNAVAILABLE"
        assert exc_info.value.status_code == 503
