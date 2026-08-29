from __future__ import annotations

from typing import Any
from uuid import uuid4

from lexigram.admin.dashboard.widget_types import ConfigField
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
    """A chart card with optional HTMX lazy-loading, filters and empty state.

    Args:
        title: Card heading.
        chart_type: Chart kind (bar/line/pie/area).
        data: Static data points rendered inline. Ignored when ``data_source``
            is set (the endpoint's response replaces the body).
        chart_config: Chart styling configuration.
        data_source: Optional endpoint URL fetched via HTMX. Filter changes
            re-fetch it with the filter values as query parameters.
        refresh_interval: Optional polling interval in seconds, only used
            when ``data_source`` is set and no filters are configured.
        description: Optional supporting text under the heading.
        col_span: Dashboard grid column span (1-4).
        filters: Optional filter schema (``ConfigField`` list) rendered above
            the chart body. Changing a filter re-fetches ``data_source`` with
            the current values; when filters are present the automatic poll
            trigger is suppressed so applied filters are not clobbered.
        empty_state_title: Override for the empty-state heading (default
            "No data").
        empty_state_message: Optional empty-state supporting text.
        empty_state_icon: Optional empty-state icon glyph.

    Example:
        ```python
        ChartWidget(
            title="Sales",
            chart_type=ChartType.BAR,
            data_source="/admin/widgets/sales/chart",
            filters=[
                ConfigField(
                    name="period",
                    type="select",
                    label="Period",
                    options=[("30d", "Last 30 days"), ("90d", "Last 90 days")],
                    default="30d",
                ),
            ],
        )
        ```
    """

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
        filters: list[ConfigField] | None = None,
        empty_state_title: str | None = None,
        empty_state_message: str | None = None,
        empty_state_icon: str | None = None,
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
        self.filters = filters or []
        self.empty_state_title = empty_state_title or "No data"
        self.empty_state_message = empty_state_message
        self.empty_state_icon = empty_state_icon
        self._body_id = f"chart-body-{uuid4().hex[:8]}"

    def _render_filters(self) -> Any:
        """Render the filter form, or ``None`` when no filters are configured."""
        if not self.filters:
            return None

        fields: list[Any] = []
        for field_schema in self.filters:
            common_attrs: dict[str, Any] = {
                "name": field_schema.name,
                "class": "bg-card border border-border rounded-md px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
            }
            if field_schema.description:
                common_attrs["title"] = field_schema.description
            if field_schema.type == "select" and field_schema.options:
                options = []
                for option_value, option_label in field_schema.options:
                    option_attrs: dict[str, Any] = {}
                    if field_schema.default is not None and str(option_value) == str(
                        field_schema.default
                    ):
                        option_attrs["selected"] = True
                    options.append(
                        el(
                            "option",
                            option_label,
                            value=str(option_value),
                            **option_attrs,
                        )
                    )
                input_el = el("select", *options, **common_attrs)
            elif field_schema.type == "boolean":
                input_el = el(
                    "input",
                    type="checkbox",
                    checked=bool(field_schema.default),
                    **common_attrs,
                )
            elif field_schema.type == "number":
                input_el = el(
                    "input",
                    type="number",
                    value=str(field_schema.default or ""),
                    **common_attrs,
                )
            else:
                input_el = el(
                    "input",
                    type="text",
                    value=str(field_schema.default or ""),
                    **common_attrs,
                )
            fields.append(
                el(
                    "label",
                    el(
                        "span",
                        field_schema.label,
                        class_="block text-xs text-muted-foreground mb-1",
                    ),
                    input_el,
                    class_="block",
                )
            )

        form_attrs: dict[str, Any] = {}
        if self.data_source:
            form_attrs.update(
                {
                    "hx-get": self.data_source,
                    "hx-trigger": "change",
                    "hx-target": f"#{self._body_id}",
                    "hx-swap": "innerHTML",
                    "hx-indicator": f"#{self._body_id}-indicator",
                }
            )
        return el(
            "form",
            *fields,
            class_="chart-filters flex flex-wrap gap-3 mb-3 items-end",
            **form_attrs,
        )

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
            if not self.filters and self.refresh_interval and self.refresh_interval > 0:
                triggers.append(f"every {self.refresh_interval * 1000}ms")
            hx_attrs["hx-get"] = self.data_source
            hx_attrs["hx-trigger"] = ", ".join(triggers)
            hx_attrs["hx-target"] = f"#{self._body_id}"
            hx_attrs["hx-swap"] = "innerHTML"
            hx_attrs["hx-indicator"] = f"#{self._body_id}-indicator"

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
            empty_children = [
                el(
                    "div",
                    self.empty_state_title,
                    class_="text-sm text-muted-foreground text-center",
                )
            ]
            if self.empty_state_icon:
                empty_children.insert(
                    0,
                    el(
                        "div",
                        self.empty_state_icon,
                        class_="text-lg mb-1 text-center",
                    ),
                )
            if self.empty_state_message:
                empty_children.append(
                    el(
                        "p",
                        self.empty_state_message,
                        class_="text-xs text-muted-foreground text-center mt-1",
                    )
                )
            body = el("div", *empty_children, class_="py-8")

        filters = self._render_filters()

        body_children: list[Any] = [body]
        if self.data_source:
            body_children.append(
                el(
                    "div",
                    el("span", "Loading chart…", class_="sr-only"),
                    class_=(
                        "htmx-indicator absolute inset-0 z-10 flex items-center "
                        "justify-center bg-card/80 rounded-lg"
                    ),
                    role="status",
                    id=f"{self._body_id}-indicator",
                )
            )

        return el(
            "div",
            el("div", *header, class_="mb-4"),
            filters,
            el(
                "div",
                *body_children,
                id=self._body_id,
                class_="relative",
                role="region",
                aria_label=self.title,
                aria_live="polite",
            ),
            class_=f"bg-card rounded-xl shadow-sm border border-border p-5 {span}".strip(),
            **hx_attrs,
        )
