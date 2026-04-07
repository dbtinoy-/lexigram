from __future__ import annotations

from lexigram.ui.charts.static import PieChart
from lexigram.ui.charts.types import ChartDataPoint


class TestPieChart:
    def test_renders_conic_gradient(self) -> None:
        data = [ChartDataPoint("A", 30, "blue"), ChartDataPoint("B", 70, "green")]
        chart = PieChart(data)
        html = str(chart.render())
        assert "conic-gradient" in html
        assert "A" in html
        assert "B" in html
        assert "30.0%" in html
        assert "70.0%" in html

    def test_empty_data(self) -> None:
        chart = PieChart([])
        html = str(chart.render())
        assert "No data" in html

    def test_single_slice(self) -> None:
        data = [ChartDataPoint("Full", 100)]
        chart = PieChart(data)
        html = str(chart.render())
        assert "100.0%" in html
