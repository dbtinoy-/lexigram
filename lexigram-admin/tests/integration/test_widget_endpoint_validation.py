"""Integration tests: widget render_endpoint validation at boot (S8)."""

from __future__ import annotations

import pytest

from lexigram.admin.di.sub_providers.contributor import AdminContributorSubProvider
from lexigram.contracts.admin import AdminRouteSpec, BaseAdminContributor
from lexigram.contracts.admin.types import DashboardWidgetDefinition


class _ValidWidgetContributor(BaseAdminContributor):
    name = "valid_widget"
    display_name = "Valid Widget"
    group = "test"
    icon = "box"
    priority = 100
    version = "1.0.0"
    package_source = "test"
    required_permissions = frozenset()

    def get_routes(self):
        return [
            AdminRouteSpec(
                path="/admin/valid_widget/render",
                method="GET",
                handler=lambda req: "",
                name="render",
            )
        ]

    def get_dashboard_widgets(self):
        return [
            DashboardWidgetDefinition(
                name="my_widget",
                title="My Widget",
                contributor="valid_widget",
                render_endpoint="/admin/valid_widget/render",
            )
        ]


class _MissingEndpointContributor(BaseAdminContributor):
    name = "missing_ep"
    display_name = "Missing EP"
    group = "test"
    icon = "box"
    priority = 200
    version = "1.0.0"
    package_source = "test"
    required_permissions = frozenset()

    def get_dashboard_widgets(self):
        return [
            DashboardWidgetDefinition(
                name="broken_widget",
                title="Broken Widget",
                contributor="missing_ep",
                render_endpoint="/admin/missing_ep/nonexistent",
            )
        ]


class TestWidgetEndpointValidation:
    async def test_valid_endpoint_no_exception(self) -> None:
        sub = AdminContributorSubProvider(contributors=[_ValidWidgetContributor])
        await sub.boot_all()

    async def test_missing_endpoint_logs_warning(self, capsys: pytest.CaptureFixture) -> None:
        sub = AdminContributorSubProvider(contributors=[_MissingEndpointContributor])
        await sub.boot_all()
        captured = capsys.readouterr()
        assert "nonexistent" in captured.out

    async def test_missing_endpoint_does_not_raise(self) -> None:
        sub = AdminContributorSubProvider(contributors=[_MissingEndpointContributor])
        await sub.boot_all()

    async def test_no_widgets_no_warning_for_contributor(self, capsys: pytest.CaptureFixture) -> None:
        class _NoWidgets(BaseAdminContributor):
            name = "no_widgets"
            display_name = "No Widgets"
            group = "test"
            icon = "box"
            priority = 300
            version = "1.0.0"
            package_source = "test"
            required_permissions = frozenset()

        sub = AdminContributorSubProvider(contributors=[_NoWidgets])
        await sub.boot_all()
        captured = capsys.readouterr()
        # no_widgets contributor should not be mentioned in warnings
        assert "no_widgets" not in captured.out
