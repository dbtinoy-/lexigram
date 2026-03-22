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

    def test_has_accessible_name(self) -> None:
        data = [ChartDataPoint("Jan", 10), ChartDataPoint("Feb", 20)]
        chart = LineChart(data)
        html = str(chart.render())
        assert 'role="img"' in html
        assert 'aria-label="Line chart: Jan: 10, Feb: 20"' in html

    def test_empty_state_has_accessible_name(self) -> None:
        chart = LineChart([])
        html = str(chart.render())
        assert 'role="img"' in html
        assert 'aria-label="Line chart: no data yet"' in html

    def test_point_titles_announce_values(self) -> None:
        data = [ChartDataPoint("Jan", 10), ChartDataPoint("Feb", 20)]
        chart = LineChart(data)
        html = str(chart.render())
        assert "<title>Jan: 10</title>" in html
        assert "<title>Feb: 20</title>" in html

    def test_negative_values_not_clipped(self) -> None:
        data = [ChartDataPoint("A", -10), ChartDataPoint("B", 10)]
        chart = LineChart(data)
        html = str(chart.render())
        assert "-10" in html

    def test_secondary_line_dashed(self) -> None:
        data = [
            ChartDataPoint("Jan", 10, secondary_value=5),
            ChartDataPoint("Feb", 20, secondary_value=8),
        ]
        chart = LineChart(data)
        html = str(chart.render())
        assert html.count("<polyline") == 2
        assert 'stroke-dasharray="4,4"' in html

    def test_color_scheme_overrides_default_blue(self) -> None:
        data = [ChartDataPoint("A", 10), ChartDataPoint("B", 20)]
        chart = LineChart(data, ChartConfig(color_scheme="green"))
        html = str(chart.render())
        assert "#22C55E" in html
