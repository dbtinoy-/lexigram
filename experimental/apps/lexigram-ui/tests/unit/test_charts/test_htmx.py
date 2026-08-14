from __future__ import annotations

from lexigram.ui.charts.htmx import chart_skeleton, hx_chart_attrs


class TestHxChartAttrs:
    def test_basic_attrs(self) -> None:
        attrs = hx_chart_attrs("/api/chart")
        assert attrs["hx-get"] == "/api/chart"
        assert "load" in attrs["hx-trigger"]

    def test_refresh_interval(self) -> None:
        attrs = hx_chart_attrs("/api/chart", refresh_interval=30)
        assert "every 30000ms" in attrs["hx-trigger"]

    def test_custom_target(self) -> None:
        attrs = hx_chart_attrs("/api/chart", target="#my-chart")
        assert attrs["hx-target"] == "#my-chart"


class TestChartSkeleton:
    def test_returns_dict(self) -> None:
        result = chart_skeleton()
        assert isinstance(result, dict)
        assert "class" in result
        assert "animate-pulse" in result["class"]
