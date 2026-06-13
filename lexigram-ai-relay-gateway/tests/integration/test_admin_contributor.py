"""Integration tests for the relay gateway admin contributor.

Covers entry-point discovery, widget route registration, read-only
page rendering with and without dependencies, widget rendering, and
the audited mutation action surface.
"""

from __future__ import annotations

from dataclasses import replace
from importlib.metadata import entry_points
from types import SimpleNamespace

import pytest

from lexigram.ai.relay.gateway.admin.contributor import RelayGatewayAdminContributor
from lexigram.ai.relay.gateway.admin.pages import (
    RelayGatewayOverviewPage,
    RelayGatewayRoutesPage,
    RelayGatewaySettingsPage,
    RelayGatewayStreamsPage,
)
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
from lexigram.contracts.core.health import HealthStatus
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


def _request() -> SimpleNamespace:
    """Build a stand-in starlette request with empty query params."""
    return SimpleNamespace(
        query_params={},
        state=SimpleNamespace(user=None),
        headers={},
    )


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


class TestContributorDiscovery:
    def test_entry_point_registered(self) -> None:
        """The contributor loads from the admin entry-point group."""
        matches = [
            ep
            for ep in entry_points(group="lexigram.admin.contributors")
            if ep.name == "relay-gateway"
        ]
        assert matches, "relay-gateway admin entry point not registered"
        loaded = matches[0].load()
        assert loaded is RelayGatewayAdminContributor

    def test_contributor_metadata(self) -> None:
        """Name, group, and permission set match the plan."""
        contributor = RelayGatewayAdminContributor()
        assert contributor.name == "relay-gateway"
        assert contributor.display_name == "Relay Gateway"
        assert contributor.group == "ai"
        assert contributor.required_permissions == frozenset(
            {
                "relay.read",
                "relay.channel_control",
                "relay.policy_control",
                "relay.manage",
            }
        )

    def test_widgets_and_pages_registered(self) -> None:
        """All dashboard widgets and management pages are declared."""
        contributor = RelayGatewayAdminContributor()
        widget_names = {w.name for w in contributor.get_dashboard_widgets()}
        assert widget_names == {"channel_health", "route_activity", "active_streams"}

        page_paths = {p.route_path for p in contributor.get_management_pages()}
        assert page_paths == {
            "/relay-gateway/overview",
            "/relay-gateway/routes",
            "/relay-gateway/streams",
            "/relay-gateway/settings",
            "/relay-gateway/channels",
        }

    def test_get_routes_returns_empty_default(self) -> None:
        """Routing is handled by lexigram-admin's WidgetController, not per-contributor."""
        contributor = RelayGatewayAdminContributor()
        assert list(contributor.get_routes()) == []

    def test_required_permissions_includes_every_declared_permission(self) -> None:
        """Every permission declared on this contributor's own surfaces must be
        in required_permissions — the coarse gate must not be narrower than what
        the contributor actually exposes."""
        contributor = RelayGatewayAdminContributor()
        declared = {
            p
            for nav in contributor.get_navigation_items()
            for p in _collect_nav_permissions(nav)
        } | {p.permission for p in contributor.get_management_pages() if p.permission}
        assert declared.issubset(contributor.required_permissions)

    def test_actions_defined(self) -> None:
        """Both mutation actions declare control permissions and schemas."""
        contributor = RelayGatewayAdminContributor()
        actions = {action.name: action for action in contributor.get_actions()}
        assert "set_channel_state" in actions
        assert "force_cancel_stream" in actions
        assert actions["set_channel_state"].permission == "relay.channel_control"
        assert actions["force_cancel_stream"].permission == "relay.stream_control"
        assert actions["force_cancel_stream"].parameter_schema is not None

    def test_read_only_pages_do_not_require_control_permissions(self) -> None:
        """Pages carry no permission gate beyond the contributor default."""
        contributor = RelayGatewayAdminContributor()
        for page in contributor.get_management_pages():
            assert page.permission in (None, "relay.read")


class TestAdminBoot:
    async def test_on_admin_boot_logs_when_dependency_resolution_fails(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A failed DI resolution degrades gracefully but is still logged."""

        class FailingContainer:
            async def resolve(self, protocol: object) -> object:
                raise UnresolvableDependencyError("service unavailable")

        contributor = RelayGatewayAdminContributor()
        await contributor.on_admin_boot(FailingContainer())

        assert contributor._health is None  # graceful degradation, unchanged
        assert contributor._metrics is None
        assert contributor._controls is None
        captured = capsys.readouterr()
        assert "relay_gateway.dependency_unavailable" in captured.out

    async def test_on_admin_boot_raises_if_an_action_handler_cannot_be_resolved(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A typo'd handler string should fail loud at boot, not at click-time."""
        from lexigram.ai.relay.gateway.admin import contributor as contributor_module

        bad_actions = (
            replace(
                contributor_module._ACTIONS[0],
                handler="lexigram.ai.relay.gateway.admin.actions:does_not_exist",
            ),
        )
        monkeypatch.setattr(contributor_module, "_ACTIONS", bad_actions)

        controls, health, metrics, _ = make_services()
        contributor = RelayGatewayAdminContributor()
        with pytest.raises(AttributeError):
            await contributor.on_admin_boot(
                FakeContainer(controls=controls, health=health, metrics=metrics)
            )


class TestReadOnlyPages:
    async def test_overview_page_renders_without_dependencies(self) -> None:
        page = RelayGatewayOverviewPage()
        response = await page.handle(_request())
        assert response.status_code == 200
        assert "Relay Gateway Overview" in response.body.decode()

    async def test_routes_page_renders_without_dependencies(self) -> None:
        page = RelayGatewayRoutesPage()
        response = await page.handle(_request())
        assert response.status_code == 200
        assert "Relay Routes" in response.body.decode()

    async def test_streams_page_renders_without_dependencies(self) -> None:
        page = RelayGatewayStreamsPage()
        response = await page.handle(_request())
        assert response.status_code == 200
        assert "Relay Streams" in response.body.decode()

    async def test_settings_page_renders_without_dependencies(self) -> None:
        page = RelayGatewaySettingsPage()
        response = await page.handle(_request())
        assert response.status_code == 200
        assert "Relay Settings" in response.body.decode()


class TestPagesWithDependencies:
    async def test_overview_shows_channel_and_stream_data(self) -> None:
        controls, health, _, _ = make_services()
        page = RelayGatewayOverviewPage(health=health, controls=controls)
        response = await page.handle(_request())
        body = response.body.decode()
        assert "claude" in body
        assert "gemini" in body

    async def test_routes_page_renders_route_table(self) -> None:
        _, _, metrics, _ = make_services()
        page = RelayGatewayRoutesPage(metrics=metrics)
        response = await page.handle(_request())
        body = response.body.decode()
        assert "Route Activity" in body

    async def test_streams_page_renders_active_streams(self) -> None:
        controls, _, _, _ = make_services()
        stream_id, _ = controls.streams.register(
            channel="claude", model="claude-sonnet", request_id="req-1"
        )
        page = RelayGatewayStreamsPage(controls=controls)
        response = await page.handle(_request())
        body = response.body.decode()
        assert stream_id in body

    async def test_settings_page_lists_policy_channels(self) -> None:
        _, _, _, store = make_services()
        page = RelayGatewaySettingsPage(policy=store)
        response = await page.handle(_request())
        body = response.body.decode()
        assert "gemini" in body
        assert "max_request_bytes" not in body


class TestWidgets:
    async def _contributor(
        self,
        *,
        controls: RelayControlsService | None = None,
        health: RelayHealthService | None = None,
        metrics: RelayMetricsService | None = None,
    ) -> RelayGatewayAdminContributor:
        contributor = RelayGatewayAdminContributor()
        await contributor.on_admin_boot(
            FakeContainer(controls=controls, health=health, metrics=metrics)
        )
        return contributor

    async def test_channel_health_widget_renders_status(self) -> None:
        _, health, _, _ = make_services()
        contributor = await self._contributor(health=health)
        result = await contributor.render_widget("channel_health", WIDGET_PARAMS)
        assert result.is_ok()
        assert "claude" in result.unwrap().body

    async def test_route_activity_widget_renders_empty_state(self) -> None:
        _, _, metrics, _ = make_services()
        contributor = await self._contributor(metrics=metrics)
        result = await contributor.render_widget("route_activity", WIDGET_PARAMS)
        assert result.is_ok()

    async def test_active_streams_widget_renders_stream(self) -> None:
        controls, _, _, _ = make_services()
        controls.streams.register(
            channel="claude", model="claude-sonnet", request_id="req-x"
        )
        contributor = await self._contributor(controls=controls)
        result = await contributor.render_widget("active_streams", WIDGET_PARAMS)
        assert result.is_ok()
        assert "claude" in result.unwrap().body

    async def test_unknown_widget_returns_error(self) -> None:
        contributor = await self._contributor()
        result = await contributor.render_widget("unknown", WIDGET_PARAMS)
        assert result.is_err()

    async def test_widgets_without_dependencies_render_unavailable(self) -> None:
        contributor = await self._contributor()
        for widget in ("channel_health", "route_activity", "active_streams"):
            result = await contributor.render_widget(widget, WIDGET_PARAMS)
            assert result.is_ok(), widget
            assert "Unavailable" in result.unwrap().body


class TestActions:
    async def _contributor(
        self,
    ) -> tuple[RelayGatewayAdminContributor, StaticPolicyStore, RecordingAudit]:
        audit_log = RecordingAudit()
        controls, _, _, store = make_services(audit=audit_log)
        contributor = RelayGatewayAdminContributor()
        await contributor.on_admin_boot(FakeContainer(controls=controls))
        return contributor, store, audit_log

    async def test_set_channel_state_success_is_audited(self) -> None:
        contributor, store, audit = await self._contributor()
        result = await contributor.execute_action(
            "set_channel_state",
            {"channel": "gemini", "enabled": False},
        )
        assert result["ok"] is True
        assert store.current.enabled_channels["gemini"] is False
        assert audit.events, "successful mutation must emit an audit event"

    async def test_set_channel_state_rejects_invalid_params(self) -> None:
        contributor, _, audit = await self._contributor()
        result = await contributor.execute_action(
            "set_channel_state",
            {"enabled": False},
        )
        assert result["ok"] is False
        assert "channel" in result["message"]
        assert not audit.events

    async def test_set_channel_state_rejects_invalid_enabled_flag(self) -> None:
        contributor, _, audit = await self._contributor()
        result = await contributor.execute_action(
            "set_channel_state",
            {"channel": "gemini", "enabled": "banana"},
        )
        assert result["ok"] is False
        assert "boolean" in result["message"]
        assert not audit.events

    async def test_force_cancel_stream_unknown_rejects(self) -> None:
        contributor, _, audit = await self._contributor()
        result = await contributor.execute_action(
            "force_cancel_stream",
            {"stream_id": "does-not-exist"},
        )
        assert result["ok"] is False
        assert not audit.events

    async def test_unknown_action_raises(self) -> None:
        contributor, _, _ = await self._contributor()
        with pytest.raises(LookupError):
            await contributor.execute_action("explode", {})


class TestHealth:
    async def _contributor(
        self, health: RelayHealthService
    ) -> RelayGatewayAdminContributor:
        contributor = RelayGatewayAdminContributor()
        await contributor.on_admin_boot(FakeContainer(health=health))
        return contributor

    async def test_render_health_check_returns_health_check_payload(self) -> None:
        """Healthy channels render a structured HEALTHY payload."""
        contributor = await self._contributor(_health_service(FakeChecker()))

        result = await contributor.render_health_check("relay.channels")

        assert result.is_ok()
        payload = result.unwrap()
        assert payload.status == HealthStatus.HEALTHY
        assert payload.component == "Relay Channels"
        assert "claude: healthy" in payload.detail
        assert "gemini: healthy" in payload.detail

    async def test_render_health_check_returns_degraded_payload_for_high_latency(
        self,
    ) -> None:
        """A degraded channel renders a structured DEGRADED payload."""
        contributor = await self._contributor(
            _health_service(FakeChecker(ok=True, latency_ms=500.0))
        )

        result = await contributor.render_health_check("relay.channels")

        assert result.is_ok()
        payload = result.unwrap()
        assert payload.status == HealthStatus.DEGRADED
        assert payload.component == "Relay Channels"

    async def test_render_health_check_returns_unhealthy_payload_for_failed_probe(
        self,
    ) -> None:
        """A failed channel renders a structured UNHEALTHY payload."""
        contributor = await self._contributor(_health_service(FakeChecker(ok=False)))

        result = await contributor.render_health_check("relay.channels")

        assert result.is_ok()
        payload = result.unwrap()
        assert payload.status == HealthStatus.UNHEALTHY
        assert payload.component == "Relay Channels"

    async def test_unknown_health_check_returns_error(self) -> None:
        """Unknown health checks return an error result."""
        contributor = RelayGatewayAdminContributor()
        result = await contributor.render_health_check("unknown")
        assert result.is_err()
