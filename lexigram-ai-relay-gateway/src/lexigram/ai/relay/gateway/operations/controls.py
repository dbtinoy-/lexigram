"""Validated runtime control service for the relay gateway.

``RelayControlsService`` applies channel drain/enable and typed policy
changes behind an explicit permission gate, persists every mutation
through a ``RelayPolicyStoreProtocol`` backend, refuses changes that
would strand the gateway without an available converter, and emits an
``AIAuditEvent`` for every applied mutation.  Audit metadata never
carries credentials, upstream URLs, prompt content, or media data.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry
from lexigram.contracts.ai.governance import (
    AIAuditEvent,
    AIAuditStoreProtocol,
    AuditEventType,
)
from lexigram.contracts.ai.relay import (
    RelayActiveStream,
    RelayGatewayError,
    RelayPolicyChange,
    RelayPolicySnapshot,
    RelayPolicyStoreProtocol,
)
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.logging import get_logger

__all__ = [
    "InMemoryRelayPolicyStore",
    "RelayControlsService",
]

logger = get_logger(__name__)

PERMISSION_READ = "relay.read"
PERMISSION_CHANNEL_CONTROL = "relay.channel_control"
PERMISSION_POLICY_CONTROL = "relay.policy_control"
PERMISSION_STREAM_CONTROL = "relay.stream_control"


class InMemoryRelayPolicyStore(RelayPolicyStoreProtocol):
    """Process-local policy store seeded from the gateway configuration.

    ``load`` always returns the current snapshot and ``save`` replaces it
    wholesale; the store is the single source of truth between control
    mutations in this process.
    """

    def __init__(self, initial: RelayPolicySnapshot) -> None:
        """Bind the store to its initial snapshot.

        Args:
            initial: Snapshot the store serves until the first save.
        """
        self._snapshot = initial

    @classmethod
    def with_defaults(cls, config: RelayGatewayConfig) -> InMemoryRelayPolicyStore:
        """Build a store seeded from a gateway configuration.

        Args:
            config: Gateway configuration; each channel contributes its
                enabled flag and declared models as the allowed options.

        Returns:
            A store whose snapshot mirrors the configuration.
        """
        enabled_channels = {
            channel.name: channel.enabled for channel in config.channels
        }
        allowed_options = {
            channel.name: frozenset(channel.models) for channel in config.channels
        }
        return cls(
            RelayPolicySnapshot(
                enabled_channels=enabled_channels,
                allowed_model_options=allowed_options,
                media_allowed_schemes=frozenset({"https"}),
                media_allowed_hosts=frozenset(),
                max_request_bytes=1024 * 1024,
                max_stream_seconds=300.0,
            )
        )

    async def load(self) -> RelayPolicySnapshot:
        """Return the current snapshot."""
        return self._snapshot

    async def save(self, snapshot: RelayPolicySnapshot) -> None:
        """Atomically replace the stored snapshot."""
        self._snapshot = snapshot


class RelayControlsService:
    """Apply permissioned, validated policy mutations for the gateway.

    Every mutation is serialized through an in-process lock, validated
    against the static channel table, persisted to the policy store, and
    audited.  A mutation that would leave the gateway without any
    enabled channel that serves at least one model option is rejected
    before persisting.
    """

    def __init__(
        self,
        registry: RelayChannelRegistry,
        store: RelayPolicyStoreProtocol,
        authorizer: AuthorizerProtocol | None = None,
        audit: AIAuditStoreProtocol | None = None,
        streams: RelayStreamRegistry | None = None,
    ) -> None:
        """Bind the controls service to its dependencies.

        Args:
            registry: Channel table defining valid channel names and
                model options.
            store: Persistent backend that owns the current snapshot.
            authorizer: Permission gate for ``relay.*`` actions. When
                ``None`` no permission check is performed (development).
            audit: Audit backend for mutation events. When ``None``
                mutations still apply without audit emission.
            streams: Registry of in-flight upstream streams. When
                ``None`` a private empty registry is created; share one
                instance with the streaming path so force-cancel reaches
                live streams.
        """
        self._registry = registry
        self._store = store
        self._authorizer = authorizer
        self._audit = audit
        self.streams = streams if streams is not None else RelayStreamRegistry()
        self._lock = asyncio.Lock()

    async def set_channel_state(
        self,
        channel: str,
        enabled: bool,
        actor_id: str,
    ) -> None:
        """Enable or drain *channel* for new requests.

        Args:
            channel: Channel name; unknown names are rejected.
            enabled: ``False`` drains the channel for new requests while
                existing streams finish.
            actor_id: Operator identity recorded in the audit event.

        Raises:
            ValueError: The channel is unknown.
            RelayGatewayError: With ``PERMISSION_DENIED`` when the actor
                lacks ``relay.channel_control``.
        """
        await self._require(actor_id, PERMISSION_CHANNEL_CONTROL, f"channel:{channel}")
        async with self._lock:
            snapshot = await self._store.load()
            if channel not in snapshot.enabled_channels:
                raise ValueError(f"unknown channel {channel!r}")
            changed = replace(
                snapshot,
                enabled_channels={**snapshot.enabled_channels, channel: enabled},
            )
            self._require_router_survives(changed)
            await self._store.save(changed)
            self._registry.set_runtime_enabled(channel, enabled)
            await self._audit_change(
                actor_id=actor_id,
                action=PERMISSION_CHANNEL_CONTROL,
                resource=channel,
                old={"enabled": not enabled},
                new={"enabled": enabled},
            )

    async def update_policy(
        self,
        change: RelayPolicyChange,
        actor_id: str,
    ) -> None:
        """Apply a typed policy change.

        Args:
            change: Partial mutation; only the fields explicitly set
                change.
            actor_id: Operator identity recorded in the audit event.

        Raises:
            ValueError: The change references an unknown channel or
                model option values, or would remove every available
                model option.
            RelayGatewayError: With ``PERMISSION_DENIED`` when the actor
                lacks ``relay.policy_control``.
        """
        await self._require(actor_id, PERMISSION_POLICY_CONTROL, "policy")
        async with self._lock:
            snapshot = await self._store.load()
            if change.channel is not None:
                if change.channel not in snapshot.enabled_channels:
                    raise ValueError(f"unknown channel {change.channel!r}")
            if change.enabled is not None and change.channel is None:
                raise ValueError("channel is required when changing enabled state")
            if change.allowed_model_options is not None and change.channel is None:
                raise ValueError(
                    "channel is required when changing allowed model options"
                )
            self._validate_options(change)
            changed = self._compose(snapshot, change)
            self._require_router_survives(changed)
            await self._store.save(changed)
            if change.enabled is not None and change.channel is not None:
                self._registry.set_runtime_enabled(change.channel, change.enabled)
            await self._audit_change(
                actor_id=actor_id,
                action=PERMISSION_POLICY_CONTROL,
                resource="policy",
                old=self._changed_fields(snapshot, change),
                new=self._changed_fields(changed, change),
            )

    async def policy_snapshot(self, actor_id: str) -> RelayPolicySnapshot:
        """Return the current runtime policy snapshot.

        Args:
            actor_id: Operator identity; ``relay.read`` permission is
                required.

        Returns:
            The snapshot persisted by the policy store.

        Raises:
            RelayGatewayError: With ``PERMISSION_DENIED`` when the actor
                lacks ``relay.read``.
        """
        await self._require(actor_id, PERMISSION_READ, "policy")
        return await self._store.load()

    def active_streams(self) -> tuple[RelayActiveStream, ...]:
        """Return the currently in-flight upstream streams.

        Returns:
            One row per active stream, oldest first; an empty tuple when
            no stream is in flight.
        """
        return self.streams.list()

    async def force_cancel_stream(
        self,
        stream_id: str,
        actor_id: str,
    ) -> None:
        """Force-cancel an in-flight upstream stream.

        Args:
            stream_id: Identifier of the stream to cancel.
            actor_id: Operator identity recorded in the audit event;
                ``relay.stream_control`` permission is required.

        Raises:
            ValueError: The stream identifier is unknown.
            RelayGatewayError: With ``PERMISSION_DENIED`` when the actor
                lacks ``relay.stream_control``.
        """
        await self._require(actor_id, PERMISSION_STREAM_CONTROL, f"stream:{stream_id}")
        if not self.streams.cancel(stream_id):
            raise ValueError(f"unknown stream {stream_id!r}")
        await self._audit_change(
            actor_id=actor_id,
            action=PERMISSION_STREAM_CONTROL,
            resource=stream_id,
            old={"cancelled": False},
            new={"cancelled": True},
        )

    def _validate_options(self, change: RelayPolicyChange) -> None:
        """Reject option names the target channel does not serve."""
        options = change.allowed_model_options
        if options is None or change.channel is None:
            return
        channel = self._channel(change.channel)
        if channel is None:
            raise ValueError(f"unknown channel {change.channel!r}")
        unknown = options - set(channel.models)
        if unknown:
            name = sorted(unknown)[0]
            raise ValueError(
                f"unknown model option {name!r} for channel {change.channel!r}"
            )

    def _channel(self, name: str):
        """Return the configured channel with *name*, or ``None``."""
        for candidate in self._registry.channels:
            if candidate.name == name:
                return candidate
        return None

    async def _require(self, actor_id: str, action: str, resource: str) -> None:
        """Enforce *action* permission, raising ``PERMISSION_DENIED``."""
        allowed = True
        if self._authorizer is not None:
            allowed = await self._authorizer.can(actor_id, action, resource)
        if not allowed:
            raise RelayGatewayError(
                code="PERMISSION_DENIED",
                message=f"{action} denied for the operator",
                status_code=403,
                request_id="",
            )

    @staticmethod
    def _compose(
        snapshot: RelayPolicySnapshot,
        change: RelayPolicyChange,
    ) -> RelayPolicySnapshot:
        """Build the snapshot after *change* is applied."""
        enabled_channels = snapshot.enabled_channels
        allowed_model_options = snapshot.allowed_model_options
        if change.enabled is not None or change.allowed_model_options is not None:
            channel = change.channel
            if channel is None:
                raise ValueError(
                    "channel is required for channel-scoped policy changes"
                )
            if change.enabled is not None:
                enabled_channels = {**enabled_channels, channel: change.enabled}
            if change.allowed_model_options is not None:
                allowed_model_options = {
                    **allowed_model_options,
                    channel: change.allowed_model_options,
                }
        return replace(
            snapshot,
            enabled_channels=enabled_channels,
            allowed_model_options=allowed_model_options,
            media_allowed_schemes=(
                change.media_allowed_schemes
                if change.media_allowed_schemes is not None
                else snapshot.media_allowed_schemes
            ),
            media_allowed_hosts=(
                change.media_allowed_hosts
                if change.media_allowed_hosts is not None
                else snapshot.media_allowed_hosts
            ),
            max_request_bytes=(
                change.max_request_bytes
                if change.max_request_bytes is not None
                else snapshot.max_request_bytes
            ),
            max_stream_seconds=(
                change.max_stream_seconds
                if change.max_stream_seconds is not None
                else snapshot.max_stream_seconds
            ),
        )

    @staticmethod
    def _require_router_survives(snapshot: RelayPolicySnapshot) -> None:
        """Reject snapshots with no enabled channel serving options.

        Raises:
            ValueError: When every channel is disabled or every
                remaining channel has no allowed model options.
        """
        for name, options in snapshot.allowed_model_options.items():
            if snapshot.enabled_channels.get(name, False) and options:
                return
        raise ValueError("policy change would remove all available converters")

    @staticmethod
    def _changed_fields(
        snapshot: RelayPolicySnapshot,
        change: RelayPolicyChange,
    ) -> dict[str, Any]:
        """Extract the values changed by *change* from *snapshot*."""
        fields: dict[str, Any] = {}
        if change.enabled is not None and change.channel is not None:
            fields[f"{change.channel}.enabled"] = snapshot.enabled_channels[
                change.channel
            ]
        if change.allowed_model_options is not None and change.channel is not None:
            fields[f"{change.channel}.allowed_model_options"] = (
                snapshot.allowed_model_options.get(change.channel, frozenset())
            )
        if change.media_allowed_schemes is not None:
            fields["media_allowed_schemes"] = snapshot.media_allowed_schemes
        if change.media_allowed_hosts is not None:
            fields["media_allowed_hosts"] = snapshot.media_allowed_hosts
        if change.max_request_bytes is not None:
            fields["max_request_bytes"] = snapshot.max_request_bytes
        if change.max_stream_seconds is not None:
            fields["max_stream_seconds"] = snapshot.max_stream_seconds
        return fields

    async def _audit_change(
        self,
        actor_id: str,
        action: str,
        resource: str,
        old: dict[str, Any],
        new: dict[str, Any],
    ) -> None:
        """Persist one audit event for an applied mutation."""
        if self._audit is None:
            return
        await self._audit.record(
            AIAuditEvent(
                event_type=AuditEventType.CONFIG_RELOADED,
                user_id=actor_id,
                status="success",
                metadata={
                    "action": action,
                    "resource": resource,
                    "old": old,
                    "new": new,
                },
            )
        )
        logger.debug(
            "relay_controls_mutated",
            action=action,
            resource=resource,
        )
