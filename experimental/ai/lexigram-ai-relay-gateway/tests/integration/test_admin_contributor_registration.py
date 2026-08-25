"""Registration and boot tests for the relay gateway admin contributor.

Covers entry-point discovery, contributor metadata, declared surfaces
(widgets, pages, actions, permissions), and graceful vs loud failure
during ``on_admin_boot``.
"""

from __future__ import annotations

from dataclasses import replace
from importlib.metadata import entry_points

import pytest

from lexigram.ai.relay.gateway.admin.contributor import RelayGatewayAdminContributor
from lexigram.contracts.exceptions.container import UnresolvableDependencyError

from admin_contributor_support import (
    FakeContainer,
    _collect_nav_permissions,
    make_services,
)


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
