from __future__ import annotations

from collections.abc import Sequence

from demo.pages.overview import OverviewPage
from demo.resources.audit_log import AuditLogResource
from demo.resources.widget import WidgetResource
from demo.settings.demo_settings import DemoSettingsPanel
from demo.widgets.widget_count import make_widget_definitions, make_widget_routes
from lexigram.contracts.admin import BaseAdminContributor
from lexigram.contracts.admin.types import (
    AdminActionDefinition,
    AdminRouteSpec,
    DashboardWidgetDefinition,
    ManagementPageDefinition,
    NavigationContribution,
    SettingsPanelDefinition,
)


class DemoContributor(BaseAdminContributor):
    name = "demo"
    display_name = "Demo Plugin"
    group = "plugins"
    icon = "puzzle"
    priority = 500
    version = "0.1.0"
    package_source = "demo"
    required_permissions = frozenset()

    def get_resources(self) -> Sequence[type]:
        return [WidgetResource, AuditLogResource]

    def get_routes(self) -> Sequence[AdminRouteSpec]:
        return [
            *make_widget_routes(),
        ]

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        return make_widget_definitions()

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        return [
            NavigationContribution(
                label="Demo Plugin",
                url="/admin",
                icon="puzzle",
                group="plugins",
                order=10,
            ),
        ]

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        return [
            ManagementPageDefinition(
                name="overview",
                title="Plugin Overview",
                contributor="demo",
                route_path="/admin/demo/overview",
                handler=OverviewPage(),
                icon="settings",
                description="Plugin overview page",
            ),
        ]

    def get_settings_panels(self) -> Sequence[SettingsPanelDefinition]:
        return [
            SettingsPanelDefinition(
                name="demo_settings",
                title="Demo Settings",
                contributor="demo",
                route_path="/admin/demo/settings",
                handler=DemoSettingsPanel(),
            ),
        ]

    def get_actions(self) -> Sequence[AdminActionDefinition]:
        return [
            AdminActionDefinition(
                name="archive_old",
                title="Archive Old Widgets",
                contributor="demo",
                handler="demo.actions.archive:handle",
            ),
        ]
