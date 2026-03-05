"""Integration tests for the AI governance admin contributor.

Covers entry-point discovery, widget route registration, read-only page
rendering with and without billing dependencies, widget rendering, and
the degraded health state when the billing store or reservation manager
is unavailable.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from importlib.metadata import entry_points
from types import SimpleNamespace

import pytest

from lexigram.ai.governance.admin import (
    GovernanceAdminContributor,
    GovernanceQuotasPage,
    GovernanceRelayUsagePage,
    GovernanceSettlementsPage,
)
from lexigram.ai.governance.relay_billing import (
    RelayReservationLimits,
    RelayReservationManager,
    RelayScopeLimit,
)
from lexigram.contracts.admin.types import WidgetParams
from lexigram.contracts.ai.governance import (
    RelayUsageRecord,
    RelayUsageScope,
    RelayUsageStoreProtocol,
)
from lexigram.contracts.ai.relay import RelayUsage


def make_scope() -> RelayUsageScope:
    """Build a RelayUsageScope with a sane default tenant."""
    return RelayUsageScope(
        tenant_id="tenant-a",
        account_id="acct-1",
        user_id="user-1",
        model="gpt-4o-mini",
        provider="openai",
        channel="default",
    )


def make_record(
    request_id: str,
    *,
    status: str = "completed",
    charge: str = "0.20",
) -> RelayUsageRecord:
    """Build a settled usage record for report tests."""
    return RelayUsageRecord(
        request_id=request_id,
        attempt_id=f"{request_id}-a1",
        scope=make_scope(),
        usage=RelayUsage(prompt_tokens=10, completion_tokens=5),
        charge=Decimal(charge),
        currency="USD",
        status=status,  # type: ignore[arg-type]
        converter_id="relay-converter",
        loss_codes=("model_not_found",) if status == "failed" else (),
    )


class FakeUsageStore(RelayUsageStoreProtocol):
    """In-memory store seeded with settled records inside the window."""

    def __init__(self) -> None:
        now = datetime.now(UTC)
        self._rows = [
            (now - timedelta(minutes=30), make_record("req-ok")),
            (
                now - timedelta(minutes=25),
                make_record("req-fail", status="failed", charge="0.30"),
            ),
        ]

    async def save_reservation(self, reservation: object) -> None:
        """No-op reservation persistence."""

    async def settle_once(self, record: RelayUsageRecord) -> RelayUsageRecord:
        """Return the record without persisting."""
        return record

    async def release(self, reservation_id: str) -> None:
        """No-op reservation release."""

    async def query(self, filters: object) -> list[RelayUsageRecord]:
        """Return rows matching the status filter only."""
        status = getattr(filters, "get", lambda key: None)("status")
        return [
            record
            for _, record in self._rows
            if status is None or record.status == status
        ]


class FakeContainer:
    """Minimal container exposing billing dependencies."""

    def __init__(
        self,
        *,
        store: RelayUsageStoreProtocol | None = None,
        manager: RelayReservationManager | None = None,
    ) -> None:
        self._services: dict[type, object] = {}
        if store is not None:
            self._services[RelayUsageStoreProtocol] = store
        if manager is not None:
            self._services[RelayReservationManager] = manager

    async def resolve(self, target: type) -> object:
        if target not in self._services:
            raise LookupError(f"unregistered {target!r}")
        return self._services[target]


def _request() -> SimpleNamespace:
    """Build a stand-in starlette request with empty query params."""
    return SimpleNamespace(query_params={}, state=SimpleNamespace(user=None), headers={})


WIDGET_PARAMS = WidgetParams(time_window_minutes=60)


class TestContributorDiscovery:
    def test_entry_point_registered(self) -> None:
        """The contributor loads from the admin entry-point group."""
        matches = [
            ep
            for ep in entry_points(group="lexigram.admin.contributors")
            if ep.name == "ai-governance"
        ]
        assert matches, "ai-governance admin entry point not registered"
        loaded = matches[0].load()
        assert loaded is GovernanceAdminContributor

    def test_contributor_metadata(self) -> None:
        """Name, group, and permission set match the plan."""
        contributor = GovernanceAdminContributor()
        assert contributor.name == "ai-governance"
        assert contributor.display_name == "AI Governance"
        assert contributor.group == "ai"
        assert contributor.required_permissions == frozenset({"governance.read"})

    def test_widgets_and_pages_registered(self) -> None:
        """All dashboard widgets and management pages are declared."""
        contributor = GovernanceAdminContributor()
        widget_names = {widget.name for widget in contributor.get_dashboard_widgets()}
        assert widget_names == {
            "current_spend",
            "token_dimensions",
            "quota_pressure",
            "settlement_failures",
        }

        page_paths = {page.route_path for page in contributor.get_management_pages()}
        assert page_paths == {
            "/ai-governance/relay-usage",
            "/ai-governance/relay-quotas",
            "/ai-governance/relay-settlements",
        }

    def test_widget_endpoints_have_matching_routes(self) -> None:
        """Every widget endpoint has a matching route registration."""
        contributor = GovernanceAdminContributor()
        route_paths = {router.path for router in contributor.get_routes()}
        for widget in contributor.get_dashboard_widgets():
            assert widget.render_endpoint in route_paths
        for health in contributor.get_health_definitions():
            assert health.check_endpoint in route_paths

    def test_read_only_pages_do_not_require_control_permissions(self) -> None:
        """Pages carry no permission gate beyond the contributor default."""
        contributor = GovernanceAdminContributor()
        for page in contributor.get_management_pages():
            assert page.permission in (None, "governance.read")


class TestReadOnlyPages:
    async def test_usage_page_renders_without_dependencies(self) -> None:
        """The usage page renders an explicit unavailable state."""
        page = GovernanceRelayUsagePage()
        response = await page.handle(_request())
        assert response.status_code == 200
        body = response.body.decode()
        assert "Relay Usage" in body
        assert "Unavailable" in body

    async def test_quotas_page_renders_without_dependencies(self) -> None:
        """The quotas page renders an explicit unavailable state."""
        page = GovernanceQuotasPage()
        response = await page.handle(_request())
        assert response.status_code == 200
        assert "Unavailable" in response.body.decode()

    async def test_settlements_page_renders_without_dependencies(self) -> None:
        """The settlements page renders an explicit unavailable state."""
        page = GovernanceSettlementsPage()
        response = await page.handle(_request())
        assert response.status_code == 200
        assert "Unavailable" in response.body.decode()


class TestPagesWithDependencies:
    async def test_usage_page_renders_report_data(self) -> None:
        """The usage page shows settled records without zeroing spend."""
        page = GovernanceRelayUsagePage(store=FakeUsageStore())
        response = await page.handle(_request())
        body = response.body.decode()
        assert "req-ok" in body
        assert "tenant-a" in body

    async def test_settlements_page_renders_failed_records(self) -> None:
        """The settlements page shows failed records and their loss codes."""
        page = GovernanceSettlementsPage(store=FakeUsageStore())
        response = await page.handle(_request())
        body = response.body.decode()
        assert "req-fail" in body
        assert "model_not_found" in body

    async def test_quotas_page_renders_quota_pressure(self) -> None:
        """The quotas page shows live reserved capacity per dimension."""
        manager = RelayReservationManager(
            RelayReservationLimits(
                tenant=RelayScopeLimit(max_tokens=1_000, max_charge=Decimal("10")),
            )
        )
        outcome = await manager.reserve("req-1", make_scope(), 400, Decimal("2.00"))
        assert outcome.is_ok()
        page = GovernanceQuotasPage(manager=manager)
        response = await page.handle(_request())
        body = response.body.decode()
        assert "tenant-a" in body
        assert "1,000" in body


class TestWidgets:
    async def _contributor(
        self,
        *,
        store: RelayUsageStoreProtocol | None = None,
        manager: RelayReservationManager | None = None,
    ) -> GovernanceAdminContributor:
        contributor = GovernanceAdminContributor()
        await contributor.on_admin_boot(
            FakeContainer(store=store, manager=manager)
        )
        return contributor

    async def test_current_spend_widget_renders_charge(self) -> None:
        """The spend widget sums the settled charge without dropping rows."""
        contributor = await self._contributor(store=FakeUsageStore())
        result = await contributor.render_widget("current_spend", WIDGET_PARAMS)
        assert result.is_ok()
        assert "0.50" in result.unwrap().body

    async def test_token_dimensions_widget_renders_totals(self) -> None:
        """The token widget renders prompt and completion totals."""
        contributor = await self._contributor(store=FakeUsageStore())
        result = await contributor.render_widget("token_dimensions", WIDGET_PARAMS)
        assert result.is_ok()
        body = result.unwrap().body
        assert "Prompt 20" in body
        assert "Completion 10" in body

    async def test_quota_pressure_widget_renders_remaining(self) -> None:
        """The quota widget renders remaining capacity per dimension."""
        manager = RelayReservationManager(
            RelayReservationLimits(
                tenant=RelayScopeLimit(max_tokens=1_000, max_charge=Decimal("10")),
            )
        )
        await manager.reserve("req-1", make_scope(), 400, Decimal("2.00"))
        contributor = await self._contributor(manager=manager)
        result = await contributor.render_widget("quota_pressure", WIDGET_PARAMS)
        assert result.is_ok()
        assert "600 tokens" in result.unwrap().body

    async def test_settlement_failures_widget_renders_count(self) -> None:
        """The failure widget counts failed settlements only."""
        contributor = await self._contributor(store=FakeUsageStore())
        result = await contributor.render_widget("settlement_failures", WIDGET_PARAMS)
        assert result.is_ok()
        assert "1" in result.unwrap().body
        assert "0.30" in result.unwrap().body

    async def test_unknown_widget_returns_error(self) -> None:
        """Unknown widget names return an error result."""
        contributor = await self._contributor()
        result = await contributor.render_widget("unknown", WIDGET_PARAMS)
        assert result.is_err()

    async def test_widgets_without_dependencies_render_unavailable(self) -> None:
        """Missing dependencies render unavailable, never zero values."""
        contributor = await self._contributor()
        for widget in (
            "current_spend",
            "token_dimensions",
            "quota_pressure",
            "settlement_failures",
        ):
            result = await contributor.render_widget(widget, WIDGET_PARAMS)
            assert result.is_ok(), widget
            assert "Unavailable" in result.unwrap().body, widget

    async def test_quota_pressure_widget_without_limits_is_honest(self) -> None:
        """An unlimited manager reports no configured limits, not zero."""
        contributor = await self._contributor(manager=RelayReservationManager())
        result = await contributor.render_widget("quota_pressure", WIDGET_PARAMS)
        assert result.is_ok()
        assert "No quota limits configured." in result.unwrap().body


class TestHealth:
    async def test_health_degraded_without_dependencies(self) -> None:
        """Missing billing dependencies report as degraded."""
        contributor = GovernanceAdminContributor()
        result = await contributor.render_health_check("governance.billing")
        assert result.is_ok()
        assert "degraded" in result.unwrap()

    async def test_health_available_with_dependencies(self) -> None:
        """Present billing dependencies report as available."""
        contributor = GovernanceAdminContributor()
        await contributor.on_admin_boot(
            FakeContainer(store=FakeUsageStore(), manager=RelayReservationManager())
        )
        result = await contributor.render_health_check("governance.billing")
        assert result.is_ok()
        assert "available" in result.unwrap()
        assert "degraded" not in result.unwrap()

    async def test_unknown_health_check_returns_error(self) -> None:
        """Unknown health checks return an error result."""
        contributor = GovernanceAdminContributor()
        result = await contributor.render_health_check("governance.unknown")
        assert result.is_err()