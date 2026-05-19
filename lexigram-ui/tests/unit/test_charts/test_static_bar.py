from __future__ import annotations

from lexigram.ui.charts.static import BarChart
from lexigram.ui.charts.types import ChartConfig, ChartDataPoint


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

    def test_has_accessible_name(self) -> None:
        data = [ChartDataPoint("A", 10), ChartDataPoint("B", 20)]
        chart = BarChart(data)
        html = str(chart.render())
        assert 'role="img"' in html
        assert 'aria-label="Bar chart: A: 10, B: 20"' in html

    def test_empty_state_has_accessible_name(self) -> None:
        chart = BarChart([])
        html = str(chart.render())
        assert 'role="img"' in html
        assert 'aria-label="Bar chart: no data yet"' in html

    def test_tooltip_reachable_by_keyboard(self) -> None:
        data = [ChartDataPoint("A", 10)]
        chart = BarChart(data)
        html = str(chart.render())
        assert "group-focus-within:opacity-100" in html

    def test_secondary_value_renders_ghost_bar(self) -> None:
        data = [ChartDataPoint("A", 60, secondary_value=30)]
        chart = BarChart(data)
        html = str(chart.render())
        assert "opacity-40" in html
        assert "width:50.0%" in html
        assert "width:100.0%" in html

    def test_color_scheme_overrides_default_blue(self) -> None:
        data = [ChartDataPoint("A", 10)]
        chart = BarChart(data, ChartConfig(color_scheme="green"))
        html = str(chart.render())
        assert 'bg-success' in html
