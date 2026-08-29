"""ChartContent edge states in the widget content renderer.

An empty point set must render an empty state (never a blank canvas) and an
unknown chart primitive must degrade to a message instead of raising.
"""

from __future__ import annotations

from lexigram.admin.dashboard.content_renderer import render_content
from lexigram.contracts.admin.widget_content import ChartContent
from lexigram.contracts.admin.widget_content import ChartPoint


class TestChartContentEdgeStates:
    def test_empty_points_render_empty_state(self) -> None:
        html = render_content(ChartContent(chart_type="bar", points=[]))
        assert "No chart data" in html
        assert "There is nothing to display" in html

    def test_unknown_chart_type_degrades_to_message(self) -> None:
        html = render_content(ChartContent(chart_type="radar", points=[]))
        assert "Unsupported chart type" in html

    def test_points_render_chart(self) -> None:
        html = render_content(
            ChartContent(
                chart_type="line",
                points=[
                    ChartPoint(label="Mon", value=4),
                    ChartPoint(label="Tue", value=7),
                ],
            )
        )
        assert "Mon" in html
        assert "Tue" in html
        assert "No chart data" not in html
