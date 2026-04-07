from __future__ import annotations

from lexigram.ui.charts.static import BarChart
from lexigram.ui.charts.types import ChartDataPoint


class TestBarChart:
    def test_renders_bars(self) -> None:
        data = [ChartDataPoint("A", 10), ChartDataPoint("B", 20)]
        chart = BarChart(data)
        html = str(chart.render())
        assert "A" in html
        assert "B" in html
        assert "10" in html
        assert "20" in html

    def test_empty_data_shows_no_data(self) -> None:
        chart = BarChart([])
        html = str(chart.render())
        assert "No data" in html

    def test_single_point(self) -> None:
        data = [ChartDataPoint("Only", 100)]
        chart = BarChart(data)
        html = str(chart.render())
        assert "Only" in html
        assert "100" in html
