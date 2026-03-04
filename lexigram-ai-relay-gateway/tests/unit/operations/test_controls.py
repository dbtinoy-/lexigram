"""Tests for the relay gateway validated operator controls.

Covers permission gating, channel and policy validation, atomic
persistence, and audit-event emission for every mutation.
"""

from __future__ import annotations

import pytest

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations.controls import RelayControlsService
from lexigram.contracts.ai.governance import AIAuditEvent, AIAuditStoreProtocol
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    RelayChannel,
    RelayFormat,
    RelayGatewayError,
    RelayPolicyChange,
    RelayPolicySnapshot,
    RelayPolicyStoreProtocol,
    RelayRegistryProtocol,
)
from lexigram.contracts.auth.guard import AuthorizerProtocol

SNAPSHOT = RelayPolicySnapshot(
    enabled_channels={"claude": True, "gemini": True},
    allowed_model_options={
        "claude": frozenset({"claude-sonnet"}),
        "gemini": frozenset({"gemini-pro"}),
    },
    media_allowed_schemes=frozenset({"https"}),
    media_allowed_hosts=frozenset({"media.example.com"}),
    max_request_bytes=4096,
    max_stream_seconds=120.0,
)


def config() -> RelayGatewayConfig:
    """Gateway config with two enabled channels."""
    return RelayGatewayConfig(
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


class StaticPolicyStore(RelayPolicyStoreProtocol):
    """In-memory policy store seeded with a fixed snapshot."""

    def __init__(self, snapshot: RelayPolicySnapshot = SNAPSHOT) -> None:
        self.current = snapshot
        self.saved: list[RelayPolicySnapshot] = []

    async def load(self) -> RelayPolicySnapshot:
        return self.current

    async def save(self, snapshot: RelayPolicySnapshot) -> None:
        self.current = snapshot
        self.saved.append(snapshot)


class FakeAuthorizer(AuthorizerProtocol):
    """Authorizer that grants or denies one action."""

    def __init__(self, allowed: set[str] | None = None) -> None:
        self.allowed = (
            allowed
            if allowed is not None
            else {
                "relay.read",
                "relay.channel_control",
                "relay.policy_control",
                "relay.stream_control",
            }
        )
        self.calls: list[tuple[str, str, str]] = []

    async def authorize(self, user: object, action: str, resource: object) -> bool:
        self.calls.append((str(user), action, str(resource)))
        return action in self.allowed

    async def check_access(
        self,
        user: object,
        allowed_roles: set[str],
        resource: str | None = None,
        action: str | None = None,
    ) -> bool:
        return False

    async def can(self, user: object, action: str, resource: str) -> bool:
        return action in self.allowed


class RecordingAudit(AIAuditStoreProtocol):
    """Captures AIAuditEvent records."""

    def __init__(self) -> None:
        self.events: list[AIAuditEvent] = []

    async def record(self, event: AIAuditEvent) -> None:
        self.events.append(event)


class FakeRegistry(RelayRegistryProtocol):
    def mapper(self, source: RelayFormat, target: RelayFormat) -> None:
        return None

    def converter_routes(self) -> tuple[tuple[RelayFormat, RelayFormat], ...]:
        return ((RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE),)

    def mapper_ids(self) -> tuple[str, ...]:
        return ("fake",)

    def converter_version(self) -> str:
        return "0.0.1"

    def route_quality(
        self, source: RelayFormat, target: RelayFormat
    ) -> ConversionQuality:
        return ConversionQuality.FAIR


def make_service(
    authorizer: FakeAuthorizer | None = None,
    store: StaticPolicyStore | None = None,
    audit: RecordingAudit | None = None,
    registry: RelayChannelRegistry | None = None,
) -> tuple[RelayControlsService, StaticPolicyStore, RecordingAudit, FakeAuthorizer]:
    """Build a controls service over a fresh registry and fakes."""
    channels = registry if registry is not None else RelayChannelRegistry(config())
    policy_store = store if store is not None else StaticPolicyStore()
    audit_log = audit if audit is not None else RecordingAudit()
    auth = authorizer if authorizer is not None else FakeAuthorizer()
    service = RelayControlsService(
        registry=channels,
        store=policy_store,
        authorizer=auth,
        audit=audit_log,
    )
    return service, policy_store, audit_log, auth


class TestChannelState:
    async def test_drain_marks_channel_disabled(self) -> None:
        service, store, audit, _ = make_service()
        await service.set_channel_state("claude", False, "admin-1")
        assert store.current.enabled_channels["claude"] is False
        assert await store.load() == store.saved[-1]

    async def test_enable_marks_channel_enabled(self) -> None:
        service, store, _, _ = make_service()
        await service.set_channel_state("gemini", False, "admin-1")
        assert store.current.enabled_channels["gemini"] is False
        await service.set_channel_state("gemini", True, "admin-1")
        assert store.current.enabled_channels["gemini"] is True

    async def test_rejects_unknown_channel(self) -> None:
        service, _, _, _ = make_service()
        with pytest.raises(ValueError, match="unknown channel"):
            await service.set_channel_state("nope", False, "admin-1")

    async def test_requires_channel_control_permission(self) -> None:
        service, _, _, auth = make_service(
            authorizer=FakeAuthorizer(allowed={"relay.policy_control"})
        )
        with pytest.raises(RelayGatewayError) as exc:
            await service.set_channel_state("claude", False, "admin-1")
        assert exc.value.code == "PERMISSION_DENIED"

    async def test_denied_mutation_is_not_audited(self) -> None:
        service, _, audit, _ = make_service(
            authorizer=FakeAuthorizer(allowed={"relay.policy_control"})
        )
        with pytest.raises(RelayGatewayError):
            await service.set_channel_state("claude", False, "admin-1")
        assert audit.events == []


def single_channel_store() -> StaticPolicyStore:
    """Policy store with only the claude channel available."""
    return StaticPolicyStore(
        RelayPolicySnapshot(
            enabled_channels={"claude": True},
            allowed_model_options={"claude": frozenset({"claude-sonnet"})},
            media_allowed_schemes=frozenset(),
            media_allowed_hosts=frozenset(),
            max_request_bytes=1,
            max_stream_seconds=1.0,
        )
    )


class TestPolicyUpdates:
    async def test_applies_typed_policy_change(self) -> None:
        service, store, _, _ = make_service()
        old = store.current
        await service.update_policy(
            RelayPolicyChange(
                max_request_bytes=2048,
                media_allowed_hosts=frozenset({"cdn.example.com"}),
            ),
            "admin-2",
        )
        current = store.current
        assert current.max_request_bytes == 2048
        assert current.media_allowed_hosts == frozenset({"cdn.example.com"})
        assert current.enabled_channels == old.enabled_channels
        assert current.allowed_model_options == old.allowed_model_options
        assert current.max_stream_seconds == old.max_stream_seconds

    async def test_requires_policy_control_permission(self) -> None:
        service, _, _, _ = make_service(
            authorizer=FakeAuthorizer(allowed={"relay.channel_control"})
        )
        with pytest.raises(RelayGatewayError) as exc:
            await service.update_policy(
                RelayPolicyChange(max_request_bytes=1), "admin-2"
            )
        assert exc.value.code == "PERMISSION_DENIED"

    async def test_rejects_invalid_option_names(self) -> None:
        service, _, _, _ = make_service()
        with pytest.raises(ValueError, match="unknown model option"):
            await service.update_policy(
                RelayPolicyChange(
                    channel="claude",
                    allowed_model_options=frozenset({"not-a-model"}),
                ),
                "admin-2",
            )

    async def test_rejects_disabling_last_available_converter(self) -> None:
        service, _, _, _ = make_service(store=single_channel_store())
        with pytest.raises(ValueError, match="remove all available converters"):
            await service.update_policy(
                RelayPolicyChange(enabled=False, channel="claude"),
                "admin-2",
            )

    async def test_rejects_clearing_last_channel_options(self) -> None:
        service, _, _, _ = make_service(store=single_channel_store())
        with pytest.raises(ValueError, match="remove all available converters"):
            await service.update_policy(
                RelayPolicyChange(channel="claude", allowed_model_options=frozenset()),
                "admin-2",
            )

    async def test_rejects_disabling_only_enabled_channel(self) -> None:
        service, _, _, _ = make_service(
            store=StaticPolicyStore(
                RelayPolicySnapshot(
                    enabled_channels={"claude": True},
                    allowed_model_options={"claude": frozenset({"claude-sonnet"})},
                    media_allowed_schemes=frozenset(),
                    media_allowed_hosts=frozenset(),
                    max_request_bytes=1,
                    max_stream_seconds=1.0,
                )
            )
        )
        with pytest.raises(ValueError, match="remove all available converters"):
            await service.set_channel_state("claude", False, "admin-2")

    async def test_unchanged_store_on_rejected_change(self) -> None:
        service, store, _, _ = make_service()
        with pytest.raises(ValueError):
            await service.update_policy(
                RelayPolicyChange(channel="nope", max_request_bytes=1), "admin-2"
            )
        assert store.current == SNAPSHOT
        assert store.saved == []


class TestDispatchDrain:
    async def test_drain_takes_channel_out_of_selection(self) -> None:
        channels = RelayChannelRegistry(config())
        service, _, _, _ = make_service(registry=channels)
        await service.set_channel_state("claude", False, "admin-1")
        selection = channels.select(RelayFormat.OPENAI_CHAT, "gemini-pro")
        assert selection.is_ok()
        assert selection.unwrap().name == "gemini"

    async def test_enable_restores_channel_in_selection(self) -> None:
        channels = RelayChannelRegistry(config())
        service, _, _, _ = make_service(registry=channels)
        await service.set_channel_state("claude", False, "admin-1")
        await service.set_channel_state("claude", True, "admin-1")
        selection = channels.select(RelayFormat.OPENAI_CHAT, "claude-sonnet")
        assert selection.is_ok()
        assert selection.unwrap().name == "claude"

    async def test_policy_change_drain_also_applies_to_selection(self) -> None:
        channels = RelayChannelRegistry(config())
        service, _, _, _ = make_service(registry=channels)
        await service.update_policy(
            RelayPolicyChange(enabled=False, channel="gemini"), "admin-2"
        )
        selection = channels.select(RelayFormat.OPENAI_CHAT, "claude-sonnet")
        assert selection.is_ok()
        assert selection.unwrap().name == "claude"


class TestAudit:
    async def test_mutation_records_audit_event(self) -> None:
        service, _, audit, _ = make_service()
        await service.set_channel_state("claude", False, "admin-1")
        assert len(audit.events) == 1
        event = audit.events[0]
        assert event.user_id == "admin-1"
        assert event.status == "success"
        assert event.metadata["action"] == "relay.channel_control"
        assert event.metadata["resource"] == "claude"
        assert event.metadata["old"] == {"enabled": True}
        assert event.metadata["new"] == {"enabled": False}

    async def test_policy_update_records_audit_event(self) -> None:
        service, _, audit, _ = make_service()
        await service.update_policy(
            RelayPolicyChange(max_stream_seconds=60.0), "admin-2"
        )
        assert len(audit.events) == 1
        event = audit.events[0]
        assert event.user_id == "admin-2"
        assert event.metadata["action"] == "relay.policy_control"
        assert event.metadata["old"] == {"max_stream_seconds": 120.0}
        assert event.metadata["new"] == {"max_stream_seconds": 60.0}

    async def test_audit_never_contains_credentials_or_urls(self) -> None:
        service, _, audit, _ = make_service()
        await service.set_channel_state("claude", False, "admin-1")
        raw = str(audit.events[0].metadata)
        assert "upstream" not in raw and "api_key" not in raw and "https://" not in raw


class TestPolicyRead:
    async def test_policy_snapshot_returns_current_policy(self) -> None:
        service, store, _, _ = make_service()
        assert await service.policy_snapshot("admin-1") == store.current

    async def test_policy_snapshot_requires_read_permission(self) -> None:
        service, _, _, _ = make_service(
            authorizer=FakeAuthorizer(allowed={"relay.channel_control"})
        )
        with pytest.raises(RelayGatewayError) as exc:
            await service.policy_snapshot("admin-1")
        assert exc.value.code == "PERMISSION_DENIED"


class TestStreamControl:
    async def test_force_cancel_sets_handle_of_active_stream(self) -> None:
        service, _, _, _ = make_service()
        stream_id, handle = service.streams.register(
            channel="claude", model="claude-sonnet", request_id="req-1"
        )
        await service.force_cancel_stream(stream_id, "admin-1")
        assert handle.is_set()

    async def test_force_cancel_unknown_stream_rejects(self) -> None:
        service, _, _, _ = make_service()
        with pytest.raises(ValueError, match="unknown stream"):
            await service.force_cancel_stream("nope", "admin-1")

    async def test_force_cancel_requires_stream_control_permission(self) -> None:
        service, _, _, _ = make_service(
            authorizer=FakeAuthorizer(allowed={"relay.read"})
        )
        with pytest.raises(RelayGatewayError) as exc:
            await service.force_cancel_stream("x", "admin-1")
        assert exc.value.code == "PERMISSION_DENIED"

    async def test_active_streams_lists_in_flight_streams(self) -> None:
        service, _, _, _ = make_service()
        first, _ = service.streams.register(
            channel="claude", model="claude-sonnet", request_id="req-1"
        )
        second, _ = service.streams.register(
            channel="gemini", model="gemini-pro", request_id="req-2"
        )
        active = service.active_streams()
        assert [row.stream_id for row in active] == [first, second]
        assert active[0].channel == "claude"
        assert active[0].model == "claude-sonnet"
        assert active[0].request_id == "req-1"

    async def test_active_streams_empty_when_none_in_flight(self) -> None:
        service, _, _, _ = make_service()
        assert service.active_streams() == ()
