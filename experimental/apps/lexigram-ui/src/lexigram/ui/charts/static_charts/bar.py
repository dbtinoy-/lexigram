"""Bar chart component."""

from __future__ import annotations

from typing import Any

from lexigram.ui.charts.config import bg_class
from lexigram.ui.charts.static_charts._svg_helpers import (
    _parse_height,
    _point_color,
    _series_summary,
)
from lexigram.ui.charts.types import ChartConfig, ChartDataPoint
from lexigram.ui.core.base import Component, el


class BarChart(Component):
    def __init__(
        self,
        data: list[ChartDataPoint],
        config: ChartConfig | None = None,
    ) -> None:
        super().__init__()
        self.data = data
        self.config = config or ChartConfig()

    def _parse_height(self) -> int:
        return _parse_height(self.config.height, 100)

    def _empty_state(self) -> Any:
        height = self._parse_height()
        return el(
            "svg",
            el(
                "rect",
                x="2",
                y="2",
                width="396",
                height=str(height - 4),
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
            class_="w-full",
            role="img",
            aria_label="Bar chart: no data yet",
            style=f"height:{self.config.height};",
            xmlns="http://www.w3.org/2000/svg",
        )

    def render(self) -> Any:
        if not self.data:
            return self._empty_state()

        max_value = max(d.value for d in self.data) or 1
        animate_class = (
            "transition-all duration-700 ease-out" if self.config.animate else ""
        )

        bars = []
        for point in self.data:
            pct = (point.value / max_value) * 100
            color = _point_color(point, self.config)
            bar_color = bg_class(color)
            secondary_pct = None
            if point.secondary_value is not None:
                secondary_pct = (point.secondary_value / max_value) * 100

            track_children: list[Any] = []
            if secondary_pct is not None:
                track_children.append(
                    el(
                        "div",
                        class_=f"h-4 rounded {bar_color} opacity-40",
                        style=f"width:{secondary_pct:.1f}%;",
                    )
                )
            track_children.append(
                el(
                    "div",
                    class_=f"h-4 rounded {bar_color} {animate_class}",
                    style=f"width:{pct:.1f}%;",
                )
            )

            bars.append(
                el(
                    "div",
                    el(
                        "span",
                        point.label,
                        class_="text-xs text-muted-foreground w-20 flex-shrink-0 truncate",
                    ),
                    el(
                        "div",
                        *track_children,
                        class_="flex-1 bg-muted rounded h-4 overflow-hidden flex items-end",
                    ),
                    el(
                        "span",
                        f"{point.value:g}",
                        class_="text-xs text-muted-foreground w-12 text-right flex-shrink-0 tabular-nums",
                    ),
                    el(
                        "div",
                        f"{point.label}: {point.value:g}",
                        class_="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 rounded bg-accent text-accent-foreground text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity pointer-events-none z-20 shadow-lg",
                    ),
                    class_="flex items-center gap-2 group relative",
                )
            )

        return el(
            "div",
            *bars,
            class_="space-y-2",
            role="img",
            aria_label=f"Bar chart: {_series_summary(self.data)}",
        )
