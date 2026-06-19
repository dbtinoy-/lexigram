from __future__ import annotations

from typing import Any, cast

from lexigram.ui.charts.config import bg_class, hex_color, text_class
from lexigram.ui.charts.types import ChartConfig, ChartDataPoint
from lexigram.ui.core.base import Component, el


def _parse_height(height: str, default: int) -> int:
    if height.endswith("px"):
        return int(height[:-2])
    return default


def _series_summary(data: list[ChartDataPoint]) -> str:
    return ", ".join(f"{d.label}: {d.value:g}" for d in data)


def _scheme_color(config: ChartConfig, fallback: str) -> str:
    if config.color_scheme == "auto":
        return fallback
    return config.color_scheme


def _point_color(point: ChartDataPoint, config: ChartConfig) -> str:
    if config.color_scheme != "auto" and point.color == "blue":
        return config.color_scheme
    return point.color


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
