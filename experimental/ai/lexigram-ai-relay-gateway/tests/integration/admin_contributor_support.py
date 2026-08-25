"""Shared bootstrap for the relay gateway admin contributor tests.

Provides fakes at the contract boundary (authorizer, policy store,
audit store, checker), a minimal container stand-in, and builders for
real gateway operation services over a fresh registry.
"""

from __future__ import annotations

from types import SimpleNamespace

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations.controls import RelayControlsService
from lexigram.ai.relay.gateway.operations.health import (
    RelayChannelCheckerProtocol,
    RelayChannelProbeResult,
    RelayHealthService,
)
from lexigram.ai.relay.gateway.operations.metrics import (
    RelayMetricsService,
    RelayRouteEvent,
)
from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry
from lexigram.contracts.admin.types import NavigationContribution
from lexigram.contracts.ai.governance import AIAuditEvent, AIAuditStoreProtocol
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    RelayChannel,
    RelayFormat,
    RelayPolicySnapshot,
    RelayPolicyStoreProtocol,
    RelayRegistryProtocol,
)
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.exceptions.container import UnresolvableDependencyError

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


class FakeUrl:
    """Minimal URL stand-in exposing ``path`` and a string form."""

    path = "/admin/relay-gateway/overview"

    def __str__(self) -> str:
        return "http://testserver/admin/relay-gateway/overview"


class FakeRequest:
    """Minimal ASGI request stand-in with a URL."""

    query_params: dict[str, str] = {}
    url = FakeUrl()

    @classmethod
    def with_params(cls, **params: str) -> FakeRequest:
        request = cls()
        request.query_params = params
        return request


def _collect_nav_permissions(nav: NavigationContribution) -> set[str]:
    """Collect every permission used on a nav item and its children."""
    perms = {nav.permission} if nav.permission else set()
    for child in nav.children:
        perms |= _collect_nav_permissions(child)
    return perms


class FakeChecker(RelayChannelCheckerProtocol):
    """Probe checker with a fixed outcome for every channel."""

    def __init__(self, *, ok: bool = True, latency_ms: float | None = 5.0) -> None:
        self._ok = ok
        self._latency_ms = latency_ms

    async def check(self, channel: RelayChannel) -> RelayChannelProbeResult | None:
        return RelayChannelProbeResult(ok=self._ok, latency_ms=self._latency_ms)


def _health_service(checker: RelayChannelCheckerProtocol) -> RelayHealthService:
    """Health service probing every configured channel with *checker*."""
    return RelayHealthService(
        registry=RelayChannelRegistry(config()),
        checker=checker,
        degraded_latency_ms=200.0,
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
    """Authorizer that grants every relay operation."""

    async def authorize(self, user: object, action: str, resource: object) -> bool:
        return action.startswith("relay.")

    async def check_access(
        self,
        user: object,
        allowed_roles: set[str],
        resource: str | None = None,
        action: str | None = None,
    ) -> bool:
        return True

    async def can(self, user: object, action: str, resource: str) -> bool:
        return action.startswith("relay.")


class RecordingAudit(AIAuditStoreProtocol):
    """Captures AIAuditEvent records."""

    def __init__(self) -> None:
        self.events: list[AIAuditEvent] = []

    async def record(self, event: AIAuditEvent) -> None:
        self.events.append(event)


class EmptyEvents:
    """Route event source that never reports activity."""

    async def events(self, window: object) -> tuple[RelayRouteEvent, ...]:
        return ()


class EmptyRegistry(RelayRegistryProtocol):
    """Converter registry without registered mappers."""

    def mapper(self, source: RelayFormat, target: RelayFormat) -> None:
        return None

    def converter_routes(self) -> tuple[tuple[RelayFormat, RelayFormat], ...]:
        return ()

    def mapper_ids(self) -> tuple[str, ...]:
        return ()

    def converter_version(self) -> str:
        return "0.0.1"

    def route_quality(
        self, source: RelayFormat, target: RelayFormat
    ) -> ConversionQuality:
        return ConversionQuality.DISCOURAGED


class FakeContainer:
    """Minimal container exposing gateway operation services."""

    def __init__(
        self,
        *,
        controls: RelayControlsService | None = None,
        health: RelayHealthService | None = None,
        metrics: RelayMetricsService | None = None,
        policy: RelayPolicyStoreProtocol | None = None,
    ) -> None:
        self._services: dict[type, object] = {}
        for service_type, service in (
            (RelayControlsService, controls),
            (RelayHealthService, health),
            (RelayMetricsService, metrics),
            (RelayPolicyStoreProtocol, policy),
        ):
            if service is not None:
                self._services[service_type] = service

    async def resolve(self, target: type) -> object:
        if target not in self._services:
            raise UnresolvableDependencyError(f"unregistered {target!r}")
        return self._services[target]


def make_services(
    audit: AIAuditStoreProtocol | None = None,
) -> tuple[
    RelayControlsService,
    RelayHealthService,
    RelayMetricsService,
    StaticPolicyStore,
]:
    """Build real gateway services over a fresh registry."""
    registry = RelayChannelRegistry(config())
    store = StaticPolicyStore()
    controls = RelayControlsService(
        registry=registry,
        store=store,
        authorizer=FakeAuthorizer(),
        audit=audit if audit is not None else RecordingAudit(),
        streams=RelayStreamRegistry(),
    )
    health = RelayHealthService(registry=registry, policy=store)
    metrics = RelayMetricsService(
        events=EmptyEvents(),
        converter=EmptyRegistry(),
    )
    return controls, health, metrics, store


WIDGET_PARAMS = SimpleNamespace(time_window_minutes=60)
