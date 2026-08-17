from __future__ import annotations

from lexigram.ui.charts.types import ChartConfig, ChartDataPoint, ChartType


class TestChartType:
    def test_enum_values(self) -> None:
        assert ChartType.BAR == "bar"
        assert ChartType.LINE == "line"
        assert ChartType.PIE == "pie"
        assert ChartType.AREA == "area"
        assert ChartType.SPARKLINE == "sparkline"
        assert ChartType.MINI_BAR == "mini_bar"

    def test_enum_members(self) -> None:
        assert len(ChartType) == 6


class TestChartDataPoint:
    def test_defaults(self) -> None:
        p = ChartDataPoint(label="Sales", value=42.0)
        assert p.label == "Sales"
        assert p.value == 42.0
        assert p.color == "blue"
        assert p.secondary_value is None

    def test_custom_color(self) -> None:
        p = ChartDataPoint(label="Sales", value=100, color="green")
        assert p.color == "green"

    def test_secondary_value(self) -> None:
        p = ChartDataPoint(label="Sales", value=100, secondary_value=50)
        assert p.secondary_value == 50.0


class TestChartConfig:
    def test_defaults(self) -> None:
        c = ChartConfig()
        assert c.title == ""
        assert c.height == "200px"
        assert c.show_grid is True
        assert c.show_labels is True
        assert c.animate is True
        assert c.color_scheme == "auto"

    def test_custom(self) -> None:
        c = ChartConfig(title="Sales", height="300px", show_grid=False)
        assert c.title == "Sales"
        assert c.height == "300px"
        assert c.show_grid is False
