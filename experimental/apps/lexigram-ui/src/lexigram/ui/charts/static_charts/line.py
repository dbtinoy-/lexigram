"""Line and area chart components."""

from __future__ import annotations

from typing import Any, cast

from lexigram.ui.charts.config import hex_color
from lexigram.ui.charts.static_charts._svg_helpers import (
    _parse_height,
    _scheme_color,
    _series_summary,
)
from lexigram.ui.charts.types import ChartConfig, ChartDataPoint
from lexigram.ui.core.base import Component, el


class LineChart(Component):
    def __init__(
        self,
        data: list[ChartDataPoint],
        config: ChartConfig | None = None,
        *,
        line_color: str = "blue",
        fill_area: bool = False,
    ) -> None:
        super().__init__()
        self.data = data
        self.config = config or ChartConfig()
        self.line_color = line_color
        self.fill_area = fill_area

    def _parse_height(self) -> int:
        return _parse_height(self.config.height, 200)

    def _empty_state(self) -> Any:
        height = self._parse_height()
        return el(
            "svg",
            el(
                "rect",
                x="30",
                y="30",
                width="340",
                height=str(height - 60),
                rx="4",
                ry="4",
                fill="var(--muted)",
                **{
                    "stroke": "var(--border)",
                    "stroke-width": "1.5",
                    "stroke-dasharray": "6,4",
                },
            ),
            el(
                "text",
                "No data yet",
                x="200",
                y=str(height // 2),
                **{
                    "fill": "var(--muted-foreground)",
                    "font-size": "14",
                    "text-anchor": "middle",
                    "dominant-baseline": "central",
                },
            ),
            viewBox=f"0 0 400 {height}",
            class_="w-full h-full",
            role="img",
            aria_label="Line chart: no data yet",
            style=f"height:{self.config.height};",
            xmlns="http://www.w3.org/2000/svg",
        )

    def _effective_color(self) -> str:
        if self.line_color != "blue":
            return self.line_color
        return _scheme_color(self.config, "blue")

    def render(self) -> Any:
        if not self.data:
            return self._empty_state()

        height = self._parse_height()
        width = 400
        padding = 30
        chart_w = width - padding * 2
        chart_h = height - padding * 2

        values = [d.value for d in self.data]
        data_min = min(values)
        data_max = max(values)
        max_val = max(0, data_max) or 1
        min_val = min(0, data_min)
        value_range = max_val - min_val or 1

        n = len(self.data)
        n = max(n, 2)

        hex_col = hex_color(self._effective_color())

        def _xy(point: ChartDataPoint) -> tuple[float, float]:
            x = padding + (self.data.index(point) / (n - 1)) * chart_w
            y = padding + chart_h - ((point.value - min_val) / value_range) * chart_h
            return x, y

        points_list: list[str] = []
        for point in self.data:
            x, y = _xy(point)
            points_list.append(f"{x:.1f},{y:.1f}")
        points_str = " ".join(points_list)

        fill_points = (
            f"{padding},{padding + chart_h} "
            f"{points_str} "
            f"{padding + chart_w},{padding + chart_h}"
        )

        children: list[Any] = []

        if self.config.show_grid:
            grid_lines = 4
            for g in range(grid_lines + 1):
                y = padding + chart_h - (g / grid_lines) * chart_h
                val = min_val + (g / grid_lines) * value_range
                children.append(
                    el(
                        "line",
                        x1=str(padding),
                        y1=f"{y:.1f}",
                        x2=str(padding + chart_w),
                        y2=f"{y:.1f}",
                        **{
                            "stroke": "var(--border)",
                            "stroke-width": "1",
                            "stroke-dasharray": "4,4",
                        },
                    )
                )
                if self.config.show_labels:
                    children.append(
                        el(
                            "text",
                            f"{val:g}",
                            x=str(padding - 4),
                            y=f"{y + 3:.1f}",
                            **{
                                "fill": "var(--muted-foreground)",
                                "font-size": "10",
                                "text-anchor": "end",
                            },
                        )
                    )

        if self.fill_area:
            children.append(
                el(
                    "polygon",
                    points=fill_points,
                    fill=hex_col,
                    opacity="0.1",
                )
            )

        children.append(
            el(
                "polyline",
                points=points_str,
                fill="none",
                **{
                    "stroke": hex_col,
                    "stroke-width": "2",
                    "stroke-linejoin": "round",
                    "stroke-linecap": "round",
                },
            )
        )

        if all(d.secondary_value is not None for d in self.data):
            sec_points: list[str] = []
            for i, point in enumerate(self.data):
                x = padding + (i / (n - 1)) * chart_w
                y = (
                    padding
                    + chart_h
                    - ((cast("float", point.secondary_value) - min_val) / value_range)
                    * chart_h
                )
                sec_points.append(f"{x:.1f},{y:.1f}")
            children.append(
                el(
                    "polyline",
                    points=" ".join(sec_points),
                    fill="none",
                    **{
                        "stroke": hex_col,
                        "stroke-width": "1.5",
                        "stroke-dasharray": "4,4",
                    },
                )
            )

        for point in self.data:
            x, y = _xy(point)
            children.append(
                el(
                    "g",
                    el(
                        "circle",
                        cx=f"{x:.1f}",
                        cy=f"{y:.1f}",
                        r="5",
                        fill="transparent",
                        stroke="transparent",
                    ),
                    el("title", f"{point.label}: {point.value:g}"),
                )
            )

        if self.config.show_labels:
            for i, point in enumerate(self.data):
                x = padding + (i / (n - 1)) * chart_w
                if n <= 12 or i % max(1, n // 8) == 0:
                    children.append(
                        el(
                            "text",
                            point.label,
                            x=f"{x:.1f}",
                            y=str(height - 4),
                            **{
                                "fill": "var(--muted-foreground)",
                                "font-size": "10",
                                "text-anchor": "middle",
                            },
                        )
                    )

        return el(
            "svg",
            *children,
            viewBox=f"0 0 {width} {height}",
            class_="w-full h-full",
            role="img",
            aria_label=f"Line chart: {_series_summary(self.data)}",
            style=f"height:{self.config.height};",
            xmlns="http://www.w3.org/2000/svg",
        )


class AreaChart(LineChart):
    def __init__(
        self,
        data: list[ChartDataPoint],
        config: ChartConfig | None = None,
        *,
        line_color: str = "blue",
    ) -> None:
        super().__init__(data, config, line_color=line_color, fill_area=True)
