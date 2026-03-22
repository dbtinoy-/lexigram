from __future__ import annotations

from lexigram.ui.charts.static import Sparkline
from lexigram.ui.charts.types import ChartDataPoint


class TestSparkline:
    def test_renders_svg(self) -> None:
        data = [ChartDataPoint("", 10), ChartDataPoint("", 20), ChartDataPoint("", 15)]
        chart = Sparkline(data)
        html = str(chart.render())
        assert "<svg" in html
        assert "polyline" in html

    def test_empty_data(self) -> None:
        chart = Sparkline([])
        html = str(chart.render())
        assert "<svg" in html or "h-" in html

    def test_single_point(self) -> None:
        data = [ChartDataPoint("", 42)]
        chart = Sparkline(data)
        html = str(chart.render())
        assert "polyline" in html

    def test_has_accessible_name(self) -> None:
        data = [ChartDataPoint("", 10), ChartDataPoint("", 20)]
        chart = Sparkline(data)
        html = str(chart.render())
        assert 'role="img"' in html
        assert 'aria-label="Sparkline: : 10, : 20"' in html

    def test_empty_state_has_accessible_name(self) -> None:
        chart = Sparkline([])
        html = str(chart.render())
        assert 'role="img"' in html
        assert 'aria-label="Sparkline: no data yet"' in html
