from __future__ import annotations

from lexigram.ui.charts.static import LineChart
from lexigram.ui.charts.types import ChartConfig, ChartDataPoint


class TestLineChart:
    def test_renders_svg(self) -> None:
        data = [ChartDataPoint("Jan", 10), ChartDataPoint("Feb", 20), ChartDataPoint("Mar", 15)]
        chart = LineChart(data)
        html = str(chart.render())
        assert "<svg" in html
        assert "polyline" in html

    def test_empty_data(self) -> None:
        chart = LineChart([])
        html = str(chart.render())
        assert "No data" in html

    def test_gridlines(self) -> None:
        data = [ChartDataPoint("A", 10), ChartDataPoint("B", 20)]
        chart = LineChart(data, ChartConfig(show_grid=False))
        html = str(chart.render())
        assert "stroke-dasharray" not in html

    def test_fill_area(self) -> None:
        data = [ChartDataPoint("A", 10), ChartDataPoint("B", 20)]
        chart = LineChart(data, fill_area=True)
        html = str(chart.render())
        assert "polygon" in html

    def test_labels(self) -> None:
        data = [ChartDataPoint("Jan", 10), ChartDataPoint("Feb", 20)]
        chart = LineChart(data, ChartConfig(show_labels=True))
        html = str(chart.render())
        assert "Jan" in html
        assert "Feb" in html
