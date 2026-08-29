"""ChartContent flows through the widget-fragment wrapper untouched.

``render_widget_fragment`` returns ``wrap_widget_body(vm.content, ...)`` and
``wrap_widget_body`` delegates to the shared content dispatcher, so a
contributor returning ``ChartContent`` must render an actual chart (not an
error card or a raw repr) with the widget title wrapped around it.
"""

from __future__ import annotations

from lexigram.admin.controllers.widget_content_handlers import wrap_widget_body
from lexigram.contracts.admin.widget_content import ChartContent, ChartPoint


def test_chart_content_renders_inside_widget_body() -> None:
    html = wrap_widget_body(
        ChartContent(
            chart_type="bar",
            points=(
                ChartPoint(label="users", value=3),
                ChartPoint(label="roles", value=2),
            ),
        ),
        title="Resources",
    )
    assert html.startswith("<div")
    assert "widget-title" in html
    assert "Resources" in html
    assert "users" in html
    assert "roles" in html
    assert 'role="img"' in html
    assert "widget-error-card" not in html


def test_chart_content_error_banner_rendered_with_chart() -> None:
    html = wrap_widget_body(
        ChartContent(chart_type="line", points=(ChartPoint(label="x", value=1),)),
        title="Pulse",
        error="stale data",
    )
    assert "stale data" in html
    assert "widget-content" in html
    assert 'role="img"' in html
