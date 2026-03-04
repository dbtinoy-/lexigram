"""Channel health aggregation for the relay gateway operations surface.

``RelayHealthService`` turns the static channel table and optional
runtime probes into stable ``RelayChannelHealth`` snapshots.  Probe
failures and timeouts are bounded per channel, and never leak upstream
URLs or credentials into the snapshot.  Registry diagnostics expose
converter capabilities as a failed dependency when no converter registry
is registered.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.contracts.ai.relay import (
    RelayChannel,
    RelayChannelHealth,
    RelayGatewayError,
    RelayPolicyStoreProtocol,
    RelayRegistryDiagnostics,
    RelayRegistryProtocol,
)
from lexigram.primitives import clock

__all__ = [
    "CONVERTER_ID",
    "RelayChannelCheckerProtocol",
    "RelayChannelProbeResult",
    "RelayHealthService",
]

CONVERTER_ID = "relay-converter"
"""Diagnostics identifier for the built-in relay converter."""

_MIN_PROBE_TIMEOUT_SECONDS = 0.001
"""Probe timeout floor so degenerate timeouts stay bounded."""

Status = Literal["healthy", "degraded", "unavailable", "failed"]


@dataclass(frozen=True, slots=True)
class RelayChannelProbeResult:
    """Outcome of probing one upstream channel.

    Attributes:
        ok: Whether the upstream responded within the bound.
        latency_ms: Observed latency, or ``None`` when unknown.
        failure: Human-readable failure reason, or ``None``.
    """

    ok: bool
    latency_ms: float | None = None
    failure: str | None = None


@runtime_checkable
class RelayChannelCheckerProtocol(Protocol):
    """Bounded upstream probe for a single channel.

    Implementations are free to ping any endpoint, but must not embed
    credentials in the probe; the health service records only the status
    values, never ``upstream_base_url`` or query strings.
    """

    async def check(self, channel: RelayChannel) -> RelayChannelProbeResult | None:
        """Probe *channel* and report a result.

        Args:
            channel: The channel to probe.

        Returns:
            The probe result, or ``None`` when the checker has no signal
            for this channel.
        """
        ...


class RelayHealthService:
    """Aggregate per-channel health and converter diagnostics.

    Status rules, evaluated in order per channel:

    - ``enabled=False`` config flag -> ``unavailable``
      (``channel_disabled``); the model count still reflects aliases.
    - Runtime policy drained the channel -> ``unavailable``
      (``drained``).
    - No checker registered -> ``unavailable`` (``dependency_missing``).
    - Probe returns ``None`` -> ``unavailable`` (``no_probe_result``).
    - Probe fails or exceeds the channel timeout -> ``failed``
      (``probe_failed`` / ``probe_timeout``), counting one failure.
    - Probe ok but latency at/above the degradation threshold ->
      ``degraded`` (``high_latency``).
    - Otherwise -> ``healthy``.

    The failure precedence ``failed > degraded > unavailable > healthy``
    holds because disabled/missing cases are decided before probing, and
    failures are decided before latency thresholds.
    """

    def __init__(
        self,
        registry: RelayChannelRegistry,
        checker: RelayChannelCheckerProtocol | None = None,
        converter: RelayRegistryProtocol | None = None,
        policy: RelayPolicyStoreProtocol | None = None,
        degraded_latency_ms: float = 200.0,
    ) -> None:
        """Bind the health service to its dependencies.

        Args:
            registry: Static channel table; the only source of channels.
            checker: Optional upstream probe. ``None`` means every
                channel is reported ``unavailable``.
            converter: Optional converter registry used by
                ``registry_diagnostics``. ``None`` makes diagnostics a
                failed dependency.
            policy: Optional runtime policy store. A channel drained
                through the store is reported ``unavailable`` with
                detail code ``drained``. ``None`` disables the check.
            degraded_latency_ms: Latency at/above which a working probe
                is reported ``degraded``. Defaults to 200 ms.
        """
        self._registry = registry
        self._checker = checker
        self._converter = converter
        self._policy = policy
        self._degraded_latency_ms = degraded_latency_ms

    async def channel_health(self) -> Sequence[RelayChannelHealth]:
        """Return a health snapshot per configured channel.

        Channels are reported in configuration order; every channel
        gets exactly one snapshot.

        Returns:
            One snapshot per channel, in configuration order.
        """
        checked_at = clock.now()
        drained: set[str] = set()
        if self._policy is not None:
            snapshot = await self._policy.load()
            drained = {
                name
                for name, enabled in snapshot.enabled_channels.items()
                if not enabled
            }
        snapshots: list[RelayChannelHealth] = []
        for channel in self._registry.channels:
            snapshots.append(
                await self._snapshot(channel, checked_at, channel.name in drained)
            )
        return snapshots

    async def registry_diagnostics(self) -> RelayRegistryDiagnostics:
        """Return converter capability diagnostics.

        Returns:
            Converter identifier, version, mapper ids, and supported
            route pairs.

        Raises:
            RelayGatewayError: With ``DEPENDENCY_UNAVAILABLE`` when no
                converter registry is registered.
        """
        if self._converter is None:
            raise RelayGatewayError(
                code="DEPENDENCY_UNAVAILABLE",
                message="converter registry is not registered",
                status_code=503,
                request_id="",
            )
        return RelayRegistryDiagnostics(
            converter_id=CONVERTER_ID,
            converter_version=self._converter.converter_version(),
            mapper_ids=self._converter.mapper_ids(),
            supported_routes=self._converter.converter_routes(),
        )

    async def _snapshot(
        self,
        channel: RelayChannel,
        checked_at: datetime,
        drained: bool = False,
    ) -> RelayChannelHealth:
        """Build the snapshot for one channel."""
        if not channel.enabled:
            return self._build(channel, checked_at, "unavailable", "channel_disabled")
        if drained:
            return self._build(channel, checked_at, "unavailable", "drained")
        if self._checker is None:
            return self._build(channel, checked_at, "unavailable", "dependency_missing")
        status: Status = "healthy"
        detail: str | None = None
        latency: float | None = None
        failures = 0
        try:
            probe = await self._probe(channel)
        except TimeoutError:
            probe = None
            status = "failed"
            detail = "probe_timeout"
            failures = 1
        if probe is None and status == "healthy":
            status = "unavailable"
            detail = "no_probe_result"
        elif probe is not None and not probe.ok:
            status = "failed"
            detail = "probe_failed"
            failures = 1
        elif probe is not None:
            latency = probe.latency_ms
            if latency is not None and latency >= self._degraded_latency_ms:
                status = "degraded"
                detail = "high_latency"
        return RelayChannelHealth(
            channel=channel.name,
            target=channel.target_format,
            status=status,
            model_count=len(channel.models),
            latency_ms_p50=latency,
            latency_ms_p95=latency,
            failure_count=failures,
            checked_at=checked_at,
            detail_code=detail,
        )

    async def _probe(self, channel: RelayChannel) -> RelayChannelProbeResult | None:
        """Run the probe for *channel*, bounded by its timeout.

        Args:
            channel: The channel to probe.

        Returns:
            The probe result, or ``None`` when the checker has no
            signal for the channel.

        Raises:
            asyncio.TimeoutError: When the probe exceeds the channel
                timeout; converted by the caller into a failed status.
        """
        checker = self._checker
        if checker is None:
            return None
        timeout = max(channel.timeout_seconds, _MIN_PROBE_TIMEOUT_SECONDS)
        return await asyncio.wait_for(checker.check(channel), timeout=timeout)

    @staticmethod
    def _build(
        channel: RelayChannel,
        checked_at: datetime,
        status: Status,
        detail: str | None,
    ) -> RelayChannelHealth:
        """Build a probe-free snapshot."""
        return RelayChannelHealth(
            channel=channel.name,
            target=channel.target_format,
            status=status,
            model_count=len(channel.models),
            latency_ms_p50=None,
            latency_ms_p95=None,
            failure_count=0,
            checked_at=checked_at,
            detail_code=detail,
        )
