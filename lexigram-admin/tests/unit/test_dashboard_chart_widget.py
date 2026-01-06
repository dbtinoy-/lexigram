from __future__ import annotations

from lexigram.admin.dashboard.chart_widget import ChartWidget
from lexigram.ui.charts.types import ChartConfig, ChartDataPoint, ChartType


class TestChartWidget:
    def test_renders_title(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [ChartDataPoint("A", 10)])
        html = str(widget.render())
        assert "Sales" in html

    def test_renders_description(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [], description="Monthly data")
        html = str(widget.render())
        assert "Monthly data" in html

    def test_empty_data_no_source(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [])
        html = str(widget.render())
        assert "No data" in html

    def test_empty_data_with_source_shows_skeleton(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [], data_source="/api/chart")
        html = str(widget.render())
        assert "hx-get" in html
        assert "animate-pulse" in html

    def test_col_span_class(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [], col_span=2)
        html = str(widget.render())
        assert "lg:col-span-2" in html

    def test_col_span_1_no_class(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [], col_span=1)
        html = str(widget.render())
        assert "lg:col-span" not in html

    def test_refresh_interval_adds_trigger(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [], data_source="/api/chart", refresh_interval=30)
        html = str(widget.render())
        assert "hx-trigger" in html
        assert "every" in html
