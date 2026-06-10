"""Stats overview widget with description, trend indicator and sparkline."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from lexigram.ui import Component, el

_COL_SPAN_MAP = {1: "", 2: "lg:col-span-2", 3: "lg:col-span-3", 4: "lg:col-span-4"}


class StatTrend(StrEnum):
    """Direction of a stat's trend indicator."""

    UP = "up"
    DOWN = "down"
    FLAT = "flat"


_TREND_ARROW = {
    StatTrend.UP: "▲",
    StatTrend.DOWN: "▼",
    StatTrend.FLAT: "—",
}

_TREND_COLOR = {
    StatTrend.UP: "#16a34a",
    StatTrend.DOWN: "#dc2626",
    StatTrend.FLAT: "#6b7280",
}

_SPARKLINE_W = 100.0
_SPARKLINE_H = 32.0


def _sparkline_points(values: list[float]) -> str:
    """Build an SVG polyline ``points`` string from values scaled to fit.

    Args:
        values: Numeric series to plot. Must contain at least two points.

    Returns:
        Space-separated ``x,y`` coordinates, or an empty string when too few
        points are provided.
    """
    if len(values) < 2:
        return ""
    min_value = min(values)
    max_value = max(values)
    value_range = (max_value - min_value) or 1.0
    n = len(values)
    points: list[str] = []
    for index, value in enumerate(values):
        x = (index / (n - 1)) * _SPARKLINE_W
        y = _SPARKLINE_H - ((value - min_value) / value_range) * (_SPARKLINE_H - 2) - 1
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


class StatsOverviewWidget(Component):
    """A single-number overview card (Filament stats-overview parity).

    Args:
        title: Label shown beneath the value.
        value: The headline statistic, rendered large.
        description: Optional supporting text below the title.
        icon: Optional icon glyph shown in a tinted box next to the value.
        trend: Optional direction arrow alongside the value.
        trend_value: Optional percentage delta rendered next to the trend arrow.
        sparkline_data: Optional numeric series rendered as an inline SVG sparkline.
        col_span: Dashboard grid column span (1-4, same as ``ChartWidget``).

    Example:
        ```python
        StatsOverviewWidget(
            title="Active Users",
            value="847",
            description="vs. last month",
            trend=StatTrend.UP,
            trend_value=12.5,
            sparkline_data=[620, 640, 700, 690, 760, 820, 847],
        )
        ```
    """

    def __init__(
        self,
        title: str,
        value: str,
        *,
        description: str = "",
        icon: str = "",
        trend: StatTrend | None = None,
        trend_value: float | None = None,
        sparkline_data: list[float] | None = None,
        col_span: int = 1,
    ) -> None:
        super().__init__()
        self.title = title
        self.value = value
        self.description = description
        self.icon = icon
        self.trend = trend
        self.trend_value = trend_value
        self.sparkline_data = sparkline_data or []
        self.col_span = col_span

    def render(self) -> Any:
        """Render the stat card markup."""
        span = _COL_SPAN_MAP.get(self.col_span, "")

        left: list[Any] = []
        if self.icon:
            left.append(
                el(
                    "div",
                    self.icon,
                    class_="w-10 h-10 rounded-lg bg-muted text-muted-foreground flex items-center justify-center text-lg shrink-0",
                )
            )

        value_row: list[Any] = [
            el(
                "div",
                self.value,
                class_="text-2xl font-semibold text-foreground leading-none",
            )
        ]
        if self.trend and self.trend in _TREND_ARROW:
            trend_text = _TREND_ARROW[self.trend]
            if self.trend_value is not None:
                trend_text = f"{trend_text} {self.trend_value:+.1f}%"
            value_row.append(
                el(
                    "span",
                    trend_text,
                    class_="text-xs font-medium",
                    style=f"color: {_TREND_COLOR[self.trend]}",
                )
            )

        body_children: list[Any] = [
            el("div", *value_row, class_="flex items-center gap-2"),
            el(
                "div",
                self.title,
                class_="text-xs text-muted-foreground mt-1",
            ),
        ]
        if self.description:
            body_children.append(
                el(
                    "div",
                    self.description,
                    class_="text-xs text-muted-foreground mt-0.5",
                )
            )

        children: list[Any] = [
            el(
                "div",
                *left,
                el("div", *body_children),
                class_="flex items-start gap-3",
            )
        ]
        if self.sparkline_data:
            points = _sparkline_points(self.sparkline_data)
            if points:
                children.append(
                    el(
                        "svg",
                        el(
                            "polyline",
                            points=points,
                            fill="none",
                            **{
                                "stroke": "var(--primary)",
                                "stroke-width": "2",
                                "stroke-linecap": "round",
                                "stroke-linejoin": "round",
                            },
                        ),
                        viewBox=f"0 0 {_SPARKLINE_W:.0f} {_SPARKLINE_H:.0f}",
                        preserveAspectRatio="none",
                        class_="w-full h-8 mt-4",
                    )
                )

        return el(
            "div",
            *children,
            class_=f"bg-card rounded-xl shadow-sm border border-border p-5 {span}".strip(),
        )
