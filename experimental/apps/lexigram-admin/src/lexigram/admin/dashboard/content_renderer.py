"""Host-side content renderer for structured widget content.

``WidgetController`` is the only ``lexigram-ui`` caller for widget fragments —
this module is the single dispatcher that turns a ``WidgetContent`` variant
into an HTML string, so contributors never build markup themselves. Every
tone-to-color decision lives in the ``_TONE_*`` mapping tables below.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from lexigram.contracts.admin.health_payload import HealthCheckPayload
from lexigram.contracts.admin.widget_content import (
    ChartContent,
    ChartPoint,
    EmptyContent,
    MessageContent,
    Stat,
    StatContent,
    TableContent,
    Tone,
    WidgetContent,
)
from lexigram.contracts.core.health import HealthStatus
from lexigram.ui import (
    AreaChart,
    Badge,
    BarChart,
    ChartDataPoint,
    EmptyState,
    LineChart,
    PieChart,
    el,
    render_to_string,
)

if TYPE_CHECKING:
    from lexigram.ui.atoms.badge import BadgeVariant

_TONE_TEXT_CLASS: dict[Tone, str] = {
    Tone.DEFAULT: "text-foreground",
    Tone.PRIMARY: "text-primary",
    Tone.SUCCESS: "text-success",
    Tone.WARNING: "text-warning",
    Tone.DANGER: "text-destructive",
    Tone.INFO: "text-info",
}

_TONE_BADGE_VARIANT: dict[Tone, BadgeVariant] = {
    Tone.DEFAULT: "default",
    Tone.PRIMARY: "primary",
    Tone.SUCCESS: "success",
    Tone.WARNING: "warning",
    Tone.DANGER: "danger",
    Tone.INFO: "info",
}

_HEALTH_STATUS_TONE: dict[HealthStatus, Tone] = {
    HealthStatus.HEALTHY: Tone.SUCCESS,
    HealthStatus.DEGRADED: Tone.WARNING,
    HealthStatus.UNHEALTHY: Tone.DANGER,
    HealthStatus.STARTING: Tone.INFO,
    HealthStatus.UNKNOWN: Tone.DEFAULT,
}

_TONE_CHART_COLOR: dict[Tone, str] = {
    Tone.DEFAULT: "blue",
    Tone.PRIMARY: "primary",
    Tone.SUCCESS: "green",
    Tone.WARNING: "yellow",
    Tone.DANGER: "red",
    Tone.INFO: "teal",
}

_CHART_COMPONENT: dict[str, type[Any]] = {
    "bar": BarChart,
    "line": LineChart,
    "pie": PieChart,
    "area": AreaChart,
}

_STAT_CLASS = (
    "rounded-lg border border-border bg-card p-4 flex flex-col gap-1 min-w-0 shadow-sm"
)
_STAT_LABEL_CLASS = (
    "text-xs font-semibold text-muted-foreground uppercase tracking-wider truncate"
)
_STAT_VALUE_CLASS = "text-2xl font-bold tabular-nums"
_STAT_DELTA_CLASS = "text-xs font-medium text-muted-foreground"
_TABLE_CLASS = "min-w-full divide-y divide-border border-separate border-spacing-0"
_TABLE_STYLE = "table-layout: auto; min-width: 100%; width: max-content;"
_TABLE_CONTAINER_CLASS = (
    "overflow-x-auto overflow-y-auto shadow-sm ring-1 ring-border dark:ring-border "
    "rounded-lg bg-muted-50"
)
_TABLE_CONTAINER_STYLE = (
    "max-height: min(70vh, calc(100vh - 18rem)); min-height: 200px;"
)
_TABLE_HEAD_ROW_CLASS = "bg-muted dark:bg-card-50 border-b border-border"
_TABLE_ROW_CLASS = (
    "hover:bg-muted dark:hover:bg-card-80 transition-shadow duration-150 "
    "border-b border-border last:border-0 group"
)
_TABLE_BODY_CLASS = "bg-card divide-y divide-border"
_TABLE_HEADING_CLASS = (
    "px-6 py-3 text-left text-xs font-medium uppercase tracking-wider "
    "text-muted-foreground sticky top-0 z-20 bg-muted dark:bg-background group"
)
_TABLE_CELL_CLASS = "px-6 py-4 whitespace-nowrap align-middle"
_TABLE_ZEBRA_CLASS = "bg-muted-30"
_HEALTH_BADGE_CLASS = "health-check-badge"
_HEALTH_DETAIL_CLASS = "text-sm text-muted-foreground"


def render_chart_fragment(
    chart_type: Literal["bar", "line", "pie", "area"], points: list[ChartPoint]
) -> str:
    """Render a chart fragment for live ``ChartWidget`` bodies.

    Convenience helper for chart-data endpoints: builds a
    :class:`~lexigram.contracts.admin.widget_content.ChartContent` from raw
    points and delegates to the shared content dispatcher, so empty point
    sets and unknown primitives degrade consistently.
    """
    return _render_chart_content(
        ChartContent(chart_type=chart_type, points=tuple(points))
    )


def render_stat_fragment(stats: list[Stat]) -> str:
    """Render a stat-grid fragment for live ``StatsOverviewWidget`` bodies.

    Convenience helper for stat endpoints, mirroring
    :func:`render_chart_fragment`: builds a
    :class:`~lexigram.contracts.admin.widget_content.StatContent` and
    delegates to the shared dispatcher so tone/delta rendering stays in one
    place.
    """
    return _render_stat_content(StatContent(stats=tuple(stats)))


def render_content(content: WidgetContent) -> str:
    """Render a ``WidgetContent`` variant into an HTML fragment.

    Args:
        content: Structured widget content produced by a contributor.

    Returns:
        Rendered HTML string.

    Raises:
        TypeError: If *content* is not a recognized ``WidgetContent`` variant.
    """
    if isinstance(content, StatContent):
        return _render_stat_content(content)
    if isinstance(content, TableContent):
        return _render_table_content(content)
    if isinstance(content, HealthCheckPayload):
        return _render_health_content(content)
    if isinstance(content, MessageContent):
        return render_to_string(
            el("p", content.text, class_=_TONE_TEXT_CLASS.get(content.tone, ""))
        )
    if isinstance(content, EmptyContent):
        return render_to_string(
            EmptyState(title=content.title, message=content.message, icon=content.icon)
        )
    if isinstance(content, ChartContent):
        return _render_chart_content(content)
    raise TypeError(f"unhandled WidgetContent variant: {type(content)!r}")


def _render_stat_content(content: StatContent) -> str:
    """Render a stat card grid (single stat or N-stats)."""
    cards: list[Any] = []
    for stat in content.stats:
        value_cls = f"{_STAT_VALUE_CLASS} {_TONE_TEXT_CLASS.get(stat.tone, '')}".strip()
        children: list[Any] = [
            el("p", stat.label, class_=_STAT_LABEL_CLASS),
            el("p", stat.value, class_=value_cls),
        ]
        if stat.delta:
            children.append(el("p", stat.delta, class_=_STAT_DELTA_CLASS))
        cards.append(el("div", *children, class_=_STAT_CLASS))
    count = len(content.stats)
    col_class = (
        "lg:grid-cols-4"
        if count >= 4
        else "lg:grid-cols-3" if count == 3 else "sm:grid-cols-2"
    )
    return render_to_string(
        el("div", *cards, class_=f"grid grid-cols-1 {col_class} gap-4")
    )


def _render_table_content(content: TableContent) -> str:
    """Render a table with per-cell ``Tone`` text classes."""
    if not content.rows:
        return render_to_string(
            el("p", content.empty_message, class_="text-sm text-muted-foreground")
        )
    headings = [
        el("th", column, class_=_TABLE_HEADING_CLASS) for column in content.columns
    ]
    body_rows: list[Any] = []
    for index, row in enumerate(content.rows):
        row_class = _TABLE_ROW_CLASS
        if index % 2 == 1:
            row_class += " " + _TABLE_ZEBRA_CLASS
        cells = [
            el(
                "td",
                cell.text,
                class_=_TONE_TEXT_CLASS.get(cell.tone, "") + " " + _TABLE_CELL_CLASS,
            )
            for cell in row
        ]
        body_rows.append(el("tr", *cells, class_=row_class))
    return render_to_string(
        el(
            "div",
            el(
                "table",
                el(
                    "thead",
                    el("tr", *headings, class_=_TABLE_HEAD_ROW_CLASS),
                ),
                el("tbody", *body_rows, class_=_TABLE_BODY_CLASS),
                class_=_TABLE_CLASS,
                style=_TABLE_STYLE,
            ),
            class_=_TABLE_CONTAINER_CLASS,
            style=_TABLE_CONTAINER_STYLE,
        )
    )


def _render_health_content(payload: HealthCheckPayload) -> str:
    """Render a health check as a status badge plus optional detail."""
    tone = _HEALTH_STATUS_TONE[payload.status]
    children: list[Any] = [
        Badge(text=payload.status.value, variant=_TONE_BADGE_VARIANT[tone])
    ]
    if payload.detail:
        children.append(el("span", f" — {payload.detail}", class_=_HEALTH_DETAIL_CLASS))
    if payload.latency_ms is not None:
        children.append(
            el("span", f" — {payload.latency_ms:.0f}ms", class_=_HEALTH_DETAIL_CLASS)
        )
    return render_to_string(el("div", *children, class_=_HEALTH_BADGE_CLASS))


def _render_chart_content(content: ChartContent) -> str:
    """Render chart points with the declared chart primitive and tone colors.

    Empty point sets render ``EmptyState`` instead of an empty canvas, and an
    unknown chart primitive degrades to a message rather than raising.
    """
    chart_cls = _CHART_COMPONENT.get(content.chart_type)
    if chart_cls is None:
        return render_to_string(
            el(
                "p",
                f"Unsupported chart type: {content.chart_type}",
                class_="text-sm text-muted-foreground text-center py-8",
            )
        )
    if not content.points:
        return render_to_string(
            EmptyState(
                title="No chart data",
                message="There is nothing to display for this widget yet.",
            )
        )
    points = [
        ChartDataPoint(
            label=point.label,
            value=point.value,
            color=_TONE_CHART_COLOR[point.tone],
            secondary_value=point.secondary_value,
        )
        for point in content.points
    ]
    return render_to_string(chart_cls(points))


__all__ = ["render_chart_fragment", "render_content", "render_stat_fragment"]
