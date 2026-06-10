from __future__ import annotations

from lexigram.admin.dashboard.stats_widget import StatTrend, StatsOverviewWidget


class TestStatsOverviewWidget:
    def test_renders_title_and_value(self) -> None:
        html = str(StatsOverviewWidget("Users", "847").render())
        assert "Users" in html
        assert "847" in html

    def test_renders_description(self) -> None:
        html = str(
            StatsOverviewWidget("Users", "847", description="vs. last month").render()
        )
        assert "vs. last month" in html

    def test_renders_icon(self) -> None:
        html = str(StatsOverviewWidget("Users", "847", icon="x").render())
        assert 'class="w-10 h-10 rounded-lg bg-muted text-muted-foreground flex items-center justify-center text-lg shrink-0"' in html
        assert ">x<" in html

    def test_trend_up_with_percentage(self) -> None:
        html = str(
            StatsOverviewWidget("Users", "847", trend=StatTrend.UP, trend_value=12.5).render()
        )
        assert "▲ +12.5%" in html
        assert "color: #16a34a" in html

    def test_trend_down_no_value(self) -> None:
        html = str(StatsOverviewWidget("Users", "847", trend=StatTrend.DOWN).render())
        assert "▼" in html
        assert "25%" not in html

    def test_trend_flat(self) -> None:
        html = str(StatsOverviewWidget("Users", "847", trend=StatTrend.FLAT).render())
        assert "—" in html

    def test_no_trend_no_arrow(self) -> None:
        html = str(StatsOverviewWidget("Users", "847").render())
        assert "▲" not in html
        assert "▼" not in html

    def test_sparkline_renders_polyline(self) -> None:
        html = str(
            StatsOverviewWidget(
                "Users", "847", sparkline_data=[620, 640, 700, 690, 760, 820, 847]
            ).render()
        )
        assert "<svg" in html
        assert "<polyline" in html
        assert "points=" in html
        assert 'stroke-width' in html

    def test_no_sparkline_when_empty(self) -> None:
        html = str(StatsOverviewWidget("Users", "847").render())
        assert "<svg" not in html

    def test_no_sparkline_when_single_point(self) -> None:
        html = str(StatsOverviewWidget("Users", "847", sparkline_data=[42]).render())
        assert "<svg" not in html

    def test_col_span_class(self) -> None:
        html = str(StatsOverviewWidget("Users", "847", col_span=3).render())
        assert "lg:col-span-3" in html

    def test_col_span_1_no_class(self) -> None:
        html = str(StatsOverviewWidget("Users", "847").render())
        assert "lg:col-span" not in html