"""Pie chart component."""

from __future__ import annotations

from typing import Any

from lexigram.ui.charts.config import bg_class, hex_color, text_class
from lexigram.ui.charts.static_charts._svg_helpers import _point_color
from lexigram.ui.charts.types import ChartConfig, ChartDataPoint
from lexigram.ui.core.base import Component, el


class PieChart(Component):
    def __init__(
        self,
        data: list[ChartDataPoint],
        config: ChartConfig | None = None,
        *,
        size: int = 160,
    ) -> None:
        super().__init__()
        self.data = data
        self.config = config or ChartConfig()
        self.size = size

    def _empty_state(self) -> Any:
        size = self.size
        cx = cy = size / 2
        r = size / 2 - 10
        return el(
            "svg",
            el(
                "circle",
                cx=str(cx),
                cy=str(cy),
                r=str(r),
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
                x=str(cx),
                y=str(cy),
                **{
                    "fill": "var(--muted-foreground)",
                    "font-size": "12",
                    "text-anchor": "middle",
                    "dominant-baseline": "central",
                },
            ),
            viewBox=f"0 0 {size} {size}",
            class_="w-full flex justify-center",
            role="img",
            aria_label="Pie chart: no data yet",
            style=f"height:{size}px;",
            xmlns="http://www.w3.org/2000/svg",
        )

    def render(self) -> Any:
        if not self.data:
            return self._empty_state()

        total = sum(d.value for d in self.data) or 1

        gradient_parts: list[str] = []
        cumulative = 0.0
        for point in self.data:
            pct = (point.value / total) * 100
            color = _point_color(point, self.config)
            hex_col = hex_color(color)
            start_pct = cumulative
            end_pct = cumulative + pct
            gradient_parts.append(f"{hex_col} {start_pct:.1f}% {end_pct:.1f}%")
            cumulative = end_pct

        conic_gradient = f"conic-gradient({', '.join(gradient_parts)})"

        pie = el(
            "div",
            class_="rounded-full",
            style=f"width:{self.size}px;height:{self.size}px;background:{conic_gradient};",
        )

        legend_items = []
        for point in self.data:
            pct = (point.value / total) * 100
            color = _point_color(point, self.config)
            dot_class = bg_class(color)
            txt_class = text_class(color)
            legend_items.append(
                el(
                    "div",
                    el(
                        "span", class_=f"w-3 h-3 rounded-full {dot_class} flex-shrink-0"
                    ),
                    el(
                        "span",
                        point.label,
                        class_="text-xs text-foreground",
                    ),
                    el(
                        "span",
                        f"{pct:.1f}%",
                        class_=f"text-xs font-medium {txt_class} ml-auto tabular-nums",
                    ),
                    el(
                        "div",
                        f"{point.label}: {point.value:g} ({pct:.1f}%)",
                        class_="absolute -top-6 left-1/2 -translate-x-1/2 px-2 py-1 rounded bg-accent text-accent-foreground text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity pointer-events-none z-20 shadow-lg",
                    ),
                    class_="flex items-center gap-2 group relative",
                )
            )

        legend = el("div", *legend_items, class_="space-y-1.5")

        summary = ", ".join(
            f"{d.label}: {d.value:g} ({d.value / total * 100:.1f}%)" for d in self.data
        )

        return el(
            "div",
            el("div", pie, class_="flex justify-center"),
            legend,
            class_="space-y-4",
            role="img",
            aria_label=f"Pie chart: {summary}",
        )
