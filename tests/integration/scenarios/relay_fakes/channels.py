"""Fake relay operations and control for scenario tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from lexigram.contracts.ai.relay.operations import (
    RelayActiveStream,
    RelayChannelHealth,
    RelayOperationsControlProtocol,
    RelayOperationsProtocol,
    RelayPolicyChange,
    RelayPolicySnapshot,
    RelayRegistryDiagnostics,
    RelayRouteMetrics,
    TimeWindow,
)


@dataclass
class FakeRelayOperations(RelayOperationsProtocol):
    """Read-only operations surface with scripted snapshots.

    Attributes:
        health: Channel health snapshots returned by ``channel_health``.
        routes: Route metrics returned by ``route_metrics``.
        diagnostics: Registry diagnostics instance.
        policy: Policy snapshot returned by ``policy_snapshot``.
        streams: Active stream rows returned by ``active_streams``.
        calls: Record of operation call names.
    """

    health: list[RelayChannelHealth] = field(default_factory=list)
    routes: list[RelayRouteMetrics] = field(default_factory=list)
    diagnostics: RelayRegistryDiagnostics | None = None
    policy: RelayPolicySnapshot | None = None
    streams: list[RelayActiveStream] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)

    async def channel_health(self) -> Sequence[RelayChannelHealth]:
        """Return the scripted health snapshots."""
        self.calls.append("channel_health")
        return self.health

    async def route_metrics(self, window: TimeWindow) -> Sequence[RelayRouteMetrics]:
        """Record the window and return the scripted route metrics."""
        del window
        self.calls.append("route_metrics")
        return self.routes

    async def registry_diagnostics(self) -> RelayRegistryDiagnostics:
        """Record and return the scripted diagnostics."""
        self.calls.append("registry_diagnostics")
        if self.diagnostics is None:
            return RelayRegistryDiagnostics(
                converter_id="fake",
                converter_version="0.0.0",
                mapper_ids=(),
                supported_routes=(),
            )
        return self.diagnostics

    async def policy_snapshot(self) -> RelayPolicySnapshot:
        """Record and return the scripted policy snapshot."""
        self.calls.append("policy_snapshot")
        if self.policy is None:
            raise AssertionError("FakeRelayOperations.policy is not configured")
        return self.policy

    async def active_streams(self) -> Sequence[RelayActiveStream]:
        """Record and return the scripted active streams."""
        self.calls.append("active_streams")
        return self.streams


@dataclass
class FakeRelayOperationsControl(RelayOperationsControlProtocol):
    """Permissioned control surface recording every mutation.

    Attributes:
        channels: Channel name to enabled flag.
        policies: Policy changes applied.
        cancelled: Stream ids force-cancelled.
        actors: Actor ids seen.
    """

    channels: dict[str, bool] = field(default_factory=dict)
    policies: list[RelayPolicyChange] = field(default_factory=list)
    cancelled: list[str] = field(default_factory=list)
    actors: list[str] = field(default_factory=list)

    async def set_channel_state(
        self, channel: str, enabled: bool, actor_id: str
    ) -> None:
        """Record a channel drain/enable mutation."""
        self.channels[channel] = enabled
        self.actors.append(actor_id)

    async def update_policy(self, change: RelayPolicyChange, actor_id: str) -> None:
        """Record a policy mutation."""
        self.policies.append(change)
        self.actors.append(actor_id)

    async def policy_snapshot(self, actor_id: str) -> RelayPolicySnapshot:
        """Record a read and return the last stored policy, when present."""
        self.actors.append(actor_id)
        if not self.policies and not self.channels:
            raise AssertionError("FakeRelayOperationsControl has no policy data")
        channel_map = dict(self.channels) or {"claude": True}
        return RelayPolicySnapshot(
            enabled_channels=channel_map,
            allowed_model_options={},
            media_allowed_schemes=frozenset(),
            media_allowed_hosts=frozenset(),
            max_request_bytes=1024 * 1024,
            max_stream_seconds=60.0,
        )

    async def force_cancel_stream(self, stream_id: str, actor_id: str) -> None:
        """Record a stream cancellation."""
        self.cancelled.append(stream_id)
        self.actors.append(actor_id)
