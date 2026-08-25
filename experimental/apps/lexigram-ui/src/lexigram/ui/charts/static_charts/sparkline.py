"""Sparkline and mini bar components."""

from __future__ import annotations

from typing import Any

from lexigram.ui.charts.config import bg_class, hex_color
from lexigram.ui.charts.static_charts._svg_helpers import _series_summary
from lexigram.ui.charts.types import ChartDataPoint
from lexigram.ui.core.base import Component, el


class Sparkline(Component):
    def __init__(
        self,
        data: list[ChartDataPoint],
        *,
        line_color: str = "blue",
        height: int = 32,
        width: int = 80,
        show_area: bool = False,
    ) -> None:
        super().__init__()
        self.data = data
        self.line_color = line_color
        self.height = height
        self.width = width
        self.show_area = show_area

    def render(self) -> Any:
        if not self.data:
            return el(
                "div",
                class_=f"h-[{self.height}px] w-[{self.width}px]",
                role="img",
                aria_label="Sparkline: no data yet",
            )

        values = [d.value for d in self.data]
        max_val = max(values) or 1
        min_val = min(values) or 0
        rng = max_val - min_val or 1
        n = len(values)
        n = max(n, 2)

        hex_col = hex_color(self.line_color)
        padding = 2
        chart_w = self.width - padding * 2
        chart_h = self.height - padding * 2

        pts: list[str] = []
        for i, v in enumerate(values):
            x = padding + (i / (n - 1)) * chart_w
            y = padding + chart_h - ((v - min_val) / rng) * chart_h
            pts.append(f"{x:.1f},{y:.1f}")
        pts_str = " ".join(pts)

        children: list[Any] = []

        if self.show_area:
            first_x, _ = pts[0].split(",") if pts else ("0", "0")
            last_x, _ = pts[-1].split(",") if pts else (str(self.width), "0")
            area_pts = (
                f"{first_x},{padding + chart_h} {pts_str} {last_x},{padding + chart_h}"
            )
            children.append(
                el("polygon", points=area_pts, fill=hex_col, opacity="0.15")
            )

        children.append(
            el(
                "polyline",
                points=pts_str,
                fill="none",
                **{
                    "stroke": hex_col,
                    "stroke-width": "1.5",
                    "stroke-linecap": "round",
                    "stroke-linejoin": "round",
                },
            )
        )

        for i, v in enumerate(values):
            x = padding + (i / (n - 1)) * chart_w
            y = padding + chart_h - ((v - min_val) / rng) * chart_h
            children.append(
                el(
                    "g",
                    el(
                        "circle",
                        cx=f"{x:.1f}",
                        cy=f"{y:.1f}",
                        r="4",
                        fill="transparent",
                        stroke="transparent",
                    ),
                    el("title", f"{self.data[i].label}: {v:g}"),
                )
            )

        return el(
            "svg",
            *children,
            viewBox=f"0 0 {self.width} {self.height}",
            class_="inline-block",
            role="img",
            aria_label=f"Sparkline: {_series_summary(self.data)}",
            style=f"width:{self.width}px;height:{self.height}px;",
            xmlns="http://www.w3.org/2000/svg",
        )


class MiniBar(Component):
    def __init__(
        self,
        value: float,
        max_value: float = 100,
        *,
        color: str = "blue",
        height: int = 8,
        width: int = 60,
        show_value: bool = False,
    ) -> None:
        super().__init__()
        self.value = value
        self.max_value = max_value or 1
        self.color = color
        self.height = height
        self.width = width
        self.show_value = show_value

    def render(self) -> Any:
        pct = (self.value / self.max_value) * 100
        if self.value > 0:
            pct = max(pct, 2)
        if self.value <= 0:
            pct = 0.0
        bar_color = bg_class(self.color) if self.value > 0 else "bg-muted"

        children = [
            el(
                "div",
                el(
                    "div",
                    class_=f"h-full rounded {bar_color} transition-all duration-500",
                    style=f"width:{pct:.1f}%;",
                ),
                class_="w-full bg-muted rounded overflow-hidden",
                style=f"height:{self.height}px;",
            ),
        ]

        if self.show_value:
            children.append(
                el(
                    "span",
                    f"{self.value:g}",
                    class_="text-xs text-muted-foreground ml-1 tabular-nums",
                )
            )

        children.append(
            el(
                "div",
                f"{self.value:g} / {self.max_value:g}",
                class_="absolute -top-6 left-1/2 -translate-x-1/2 px-2 py-1 rounded bg-accent text-accent-foreground text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity pointer-events-none z-20 shadow-lg",
            ),
        )

        return el(
            "div",
            *children,
            class_="flex items-center gap-1 group relative",
            style=f"width:{self.width}px;" if not self.show_value else "",
            role="img",
            aria_label=f"{self.value:g} of {self.max_value:g}",
        )
