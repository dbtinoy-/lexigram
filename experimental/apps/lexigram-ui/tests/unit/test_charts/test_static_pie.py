from __future__ import annotations

from lexigram.ui.charts.static import PieChart
from lexigram.ui.charts.types import ChartConfig, ChartDataPoint


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

    def test_has_accessible_name(self) -> None:
        data = [ChartDataPoint("A", 30, "blue"), ChartDataPoint("B", 70, "green")]
        chart = PieChart(data)
        html = str(chart.render())
        assert 'role="img"' in html
        assert 'aria-label="Pie chart: A: 30 (30.0%), B: 70 (70.0%)"' in html

    def test_empty_state_has_accessible_name(self) -> None:
        chart = PieChart([])
        html = str(chart.render())
        assert 'role="img"' in html
        assert 'aria-label="Pie chart: no data yet"' in html

    def test_tooltip_reachable_by_keyboard(self) -> None:
        data = [ChartDataPoint("A", 30)]
        chart = PieChart(data)
        html = str(chart.render())
        assert "group-focus-within:opacity-100" in html

    def test_color_scheme_overrides_default_blue(self) -> None:
        data = [ChartDataPoint("A", 30), ChartDataPoint("B", 70)]
        chart = PieChart(data, config=ChartConfig(color_scheme="green"))
        html = str(chart.render())
        assert "#22C55E" in html
