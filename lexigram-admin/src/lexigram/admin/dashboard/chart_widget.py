from __future__ import annotations

from typing import Any

from lexigram.ui import (
    AreaChart,
    BarChart,
    ChartConfig,
    ChartDataPoint,
    ChartType,
    Component,
    LineChart,
    PieChart,
    el,
)

_CHART_TYPE_MAP: dict[ChartType, type[Component]] = {
    ChartType.BAR: BarChart,
    ChartType.LINE: LineChart,
    ChartType.PIE: PieChart,
    ChartType.AREA: AreaChart,
}

_COL_SPAN_MAP = {1: "", 2: "lg:col-span-2", 3: "lg:col-span-3", 4: "lg:col-span-4"}


class ChartWidget(Component):
    def __init__(
        self,
        title: str,
        chart_type: ChartType,
        data: list[ChartDataPoint] | None = None,
        *,
        chart_config: ChartConfig | None = None,
        data_source: str | None = None,
        refresh_interval: int | None = None,
        description: str = "",
        col_span: int = 1,
    ) -> None:
        super().__init__()
        self.title = title
        self.chart_type = chart_type
        self.data = data or []
        self.chart_config = chart_config or ChartConfig()
        self.data_source = data_source
        self.refresh_interval = refresh_interval
        self.description = description
        self.col_span = col_span

    def render(self) -> Any:
        span = _COL_SPAN_MAP.get(self.col_span, "")

        header = [
            el(
                "h3",
                self.title,
                class_="text-sm font-semibold text-foreground",
            ),
        ]
        if self.description:
            header.append(
                el(
                    "p",
                    self.description,
                    class_="text-xs text-muted-foreground mt-0.5",
                )
            )

        hx_attrs: dict[str, Any] = {}
        if self.data_source:
            triggers = ["load"]
            if self.refresh_interval and self.refresh_interval > 0:
                triggers.append(f"every {self.refresh_interval * 1000}ms")
            hx_attrs["hx-get"] = self.data_source
            hx_attrs["hx-trigger"] = ", ".join(triggers)
            hx_attrs["hx-swap"] = "innerHTML"

        body: Component
        if self.data:
            chart_cls = _CHART_TYPE_MAP.get(self.chart_type)
            if chart_cls:
                body = chart_cls(self.data, self.chart_config)
            else:
                body = el(
                    "div",
                    "Unsupported chart type",
                    class_="text-sm text-muted-foreground text-center py-8",
                )
        elif self.data_source:
            body = el(
                "div",
                el("div", class_="h-4 bg-muted rounded w-3/4 mb-2"),
                el("div", class_="h-4 bg-muted rounded w-1/2 mb-2"),
                class_="animate-pulse py-2",
            )
        else:
            body = el(
                "div",
                "No data",
                class_="text-sm text-muted-foreground text-center py-8",
            )

        return el(
            "div",
            el("div", *header, class_="mb-4"),
            body,
            class_=f"bg-card rounded-xl shadow-sm border border-border p-5 {span}".strip(),
            **hx_attrs,
        )
