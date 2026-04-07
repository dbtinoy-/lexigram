from __future__ import annotations

from collections.abc import Sequence

from lexigram.contracts.admin.types import AdminRouteSpec, DashboardWidgetDefinition, WidgetCategory, WidgetSize


async def widget_count_handler(request) -> str:
    return "<div><strong>42</strong> widgets tracked</div>"


def make_widget_definitions() -> Sequence[DashboardWidgetDefinition]:
    return [
        DashboardWidgetDefinition(
            name="widget_count",
            title="Widget Count",
            contributor="demo",
            render_endpoint="/admin/demo/widgets/count",
            size=WidgetSize.SMALL,
            category=WidgetCategory.METRICS,
            refresh_interval_seconds=60,
            description="Total widget count",
        ),
    ]


def make_widget_routes() -> Sequence[AdminRouteSpec]:
    return [
        AdminRouteSpec(
            path="/admin/demo/widgets/count",
            method="GET",
            handler=widget_count_handler,
            name="widgets.count",
        ),
    ]
