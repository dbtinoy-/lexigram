"""Live/loading states for ChartWidget and StatsOverviewWidget.

Both components must expose an ``hx-indicator`` target with a ``role=status``
element so HTMX fetches are visually announced, and must keep accessible
region semantics on the swap target.
"""

from __future__ import annotations

from lexigram.admin.dashboard.chart_widget import ChartWidget
from lexigram.admin.dashboard.stats_widget import StatsOverviewWidget
from lexigram.ui import ChartDataPoint, ChartType, render_to_string


class TestChartWidgetLiveStates:
    def test_data_source_renders_indicator(self) -> None:
        widget = ChartWidget(
            title="Sales",
            chart_type=ChartType.BAR,
            data_source="/admin/widgets/sales/chart",
        )
        html = render_to_string(widget)
        assert 'hx-get="/admin/widgets/sales/chart"' in html
        assert 'hx-indicator="#chart-body-' in html
        assert 'role="status"' in html
        assert "Loading chart" in html
        assert 'aria-live="polite"' in html

    def test_static_data_renders_inline_chart(self) -> None:
        widget = ChartWidget(
            title="Sales",
            chart_type=ChartType.BAR,
            data=[
                ChartDataPoint(label="Mon", value=10),
                ChartDataPoint(label="Tue", value=20),
            ],
        )
        html = render_to_string(widget)
        assert "Mon" in html
        assert "Tue" in html
        assert "hx-get" not in html
        assert "htmx-indicator" not in html

    def test_no_data_renders_empty_state(self) -> None:
        widget = ChartWidget(
            title="Sales",
            chart_type=ChartType.BAR,
            empty_state_title="Nothing here",
            empty_state_message="Come back later.",
        )
        html = render_to_string(widget)
        assert "Nothing here" in html
        assert "Come back later." in html


class TestStatsOverviewWidgetLiveStates:
    def test_data_source_renders_skeleton_and_indicator(self) -> None:
        widget = StatsOverviewWidget(
            title="Active Users",
            value="847",
            data_source="/admin/widgets/users/stat",
            refresh_interval=30,
        )
        html = render_to_string(widget)
        assert 'hx-get="/admin/widgets/users/stat"' in html
        assert "every 30000ms" in html
        assert 'hx-indicator="#stat-body-' in html
        assert 'role="status"' in html
        assert "animate-pulse" in html
        # Live mode must not render the static value/body markup.
        assert "847" not in html

    def test_static_renders_value_and_sparkline(self) -> None:
        widget = StatsOverviewWidget(
            title="Active Users",
            value="847",
            sparkline_data=[10, 20, 15, 30],
        )
        html = render_to_string(widget)
        assert "847" in html
        assert "<svg" in html
        assert "hx-get" not in html
