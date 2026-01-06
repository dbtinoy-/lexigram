"""Dashboard widget components for lexigram-admin.

Provides production-quality widgets:
- StatCard — single metric with optional trend indicator
- StatCardGrid — responsive grid of StatCards
- ActivityFeed — recent admin events list
- SystemHealthWidget — service health at-a-glance
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.ui import Component, el, raw

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Stat:
    """A single metric for display in a StatCard.

    Attributes:
        label: Human-readable label (e.g. ``"Total Users"``).
        value: Current value as a string (e.g. ``"1,234"``).
        icon: Lucide icon name (e.g. ``"users"``).
        color: Tailwind colour token: ``"blue"``, ``"green"``, ``"red"``, ``"yellow"``, ``"purple"``, ``"gray"``.
        change: Percentage change string (e.g. ``"+12%"``). Shown when non-empty.
        change_positive: Whether the change is positive (green) or negative (red).
        description: Secondary text below the value.
        href: Optional link when card is clickable.
    """

    label: str
    value: str
    icon: str = "bar-chart-2"
    color: str = "blue"
    change: str = ""
    change_positive: bool = True
    description: str = ""
    href: str = ""


@dataclass
class ActivityItem:
    """A single item in the activity feed.

    Attributes:
        actor: Name of user who performed the action.
        action: Past-tense verb (e.g. ``"created"``).
        resource: Resource type (e.g. ``"User"``).
        resource_id: Optional ID of affected record.
        timestamp: ISO-8601 timestamp string or human-relative string (e.g. ``"2m ago"``).
        icon: Lucide icon name.
    """

    actor: str
    action: str
    resource: str
    resource_id: str = ""
    timestamp: str = ""
    icon: str = "activity"


@dataclass
class HealthEntry:
    """Health status for a single service.

    Attributes:
        name: Service name (e.g. ``"Database"``).
        status: ``"ok"``, ``"degraded"``, or ``"down"``.
        latency_ms: Optional response latency in milliseconds.
        message: Optional detail message.
    """

    name: str
    status: str = "ok"
    latency_ms: int | None = None
    message: str = ""


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

_ICON_BG: dict[str, str] = {
    "blue": "bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400",
    "green": "bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400",
    "red": "bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400",
    "yellow": "bg-yellow-100 dark:bg-yellow-900/40 text-yellow-600 dark:text-yellow-400",
    "purple": "bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400",
    "gray": "bg-gray-100 dark:bg-gray-900/40 text-gray-600 dark:text-gray-400",
    "indigo": "bg-primary-100 dark:bg-primary-900/40 text-primary-600 dark:text-primary-400",
    "orange": "bg-orange-100 dark:bg-orange-900/40 text-orange-600 dark:text-orange-400",
}

_HEALTH_COLORS: dict[str, str] = {
    "ok": "text-green-600 dark:text-green-400",
    "degraded": "text-yellow-600 dark:text-yellow-400",
    "down": "text-red-600 dark:text-red-400",
}

_HEALTH_DOT: dict[str, str] = {
    "ok": "bg-green-500",
    "degraded": "bg-yellow-500",
    "down": "bg-red-500",
}


# ---------------------------------------------------------------------------
# StatCard component
# ---------------------------------------------------------------------------


class StatCard(Component):
    """A single stat card with icon, value, label, and optional trend.

    Args:
        stat: :class:`Stat` data to render.
    """

    def __init__(self, stat: Stat) -> None:
        super().__init__()
        self.stat = stat

    def render(self) -> Any:
        s = self.stat
        icon_bg = _ICON_BG.get(s.color, _ICON_BG["blue"])

        change_el: Any = ""
        if s.change:
            color = (
                "text-green-600 dark:text-green-400"
                if s.change_positive
                else "text-red-600 dark:text-red-400"
            )
            arrow = "↑" if s.change_positive else "↓"
            change_el = el(
                "span", f"{arrow} {s.change}", class_=f"text-xs font-medium {color}"
            )

        description_el: Any = ""
        if s.description:
            description_el = el(
                "p",
                s.description,
                class_="text-xs text-gray-500 dark:text-gray-400 mt-1",
            )

        icon_el = el(
            "div",
            raw(f'<i data-lucide="{s.icon}" class="w-5 h-5"></i>'),
            class_=f"flex-shrink-0 rounded-lg p-3 {icon_bg}",
        )
        value_row = el(
            "div",
            el(
                "span",
                s.value,
                class_="text-2xl font-bold text-gray-900 dark:text-white tabular-nums",
            ),
            change_el,
            class_="flex items-baseline gap-2",
        )
        info_el = el(
            "div",
            el(
                "p",
                s.label,
                class_="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1",
            ),
            value_row,
            description_el,
            class_="flex-1 min-w-0",
        )
        inner = el(
            "div",
            icon_el,
            info_el,
            class_="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-5 flex items-start gap-4 hover:shadow-md transition-shadow",
        )

        if s.href:
            return el("a", inner, href=s.href, class_="block")
        return inner


# ---------------------------------------------------------------------------
# StatCardGrid component
# ---------------------------------------------------------------------------


class StatCardGrid(Component):
    """A responsive grid of :class:`StatCard` components.

    Args:
        stats: List of :class:`Stat` items to render.
        cols: Number of columns (2, 3, or 4). Defaults to 4.
    """

    def __init__(self, stats: list[Stat], *, cols: int = 4) -> None:
        super().__init__()
        self.stats = stats
        self.cols = cols

    def render(self) -> Any:
        col_class = {
            2: "sm:grid-cols-2",
            3: "sm:grid-cols-2 lg:grid-cols-3",
            4: "sm:grid-cols-2 lg:grid-cols-4",
        }.get(self.cols, "sm:grid-cols-2 lg:grid-cols-4")
        return el(
            "div",
            *[StatCard(s) for s in self.stats],
            class_=f"grid grid-cols-1 {col_class} gap-4",
        )


# ---------------------------------------------------------------------------
# ActivityFeed component
# ---------------------------------------------------------------------------


class ActivityFeed(Component):
    """Recent activity log feed.

    Args:
        items: List of :class:`ActivityItem` entries to render.
        title: Card heading.
        view_all_href: Optional "View all" link URL.
        max_items: Maximum items to show (0 = show all).
    """

    def __init__(
        self,
        items: list[ActivityItem],
        *,
        title: str = "Recent Activity",
        view_all_href: str = "",
        max_items: int = 8,
    ) -> None:
        super().__init__()
        self.items = items[:max_items] if max_items else items
        self.title = title
        self.view_all_href = view_all_href

    def render(self) -> Any:
        header_children: list[Any] = [
            el(
                "h3",
                self.title,
                class_="text-sm font-semibold text-gray-700 dark:text-gray-200",
            ),
        ]
        if self.view_all_href:
            header_children.append(
                el(
                    "a",
                    "View all →",
                    href=self.view_all_href,
                    class_="text-xs text-primary-500 hover:text-primary-600 dark:text-primary-400",
                )
            )

        if not self.items:
            body = el(
                "p",
                "No recent activity.",
                class_="text-sm text-gray-400 dark:text-gray-500 py-4 text-center",
            )
        else:
            rows = []
            for item in self.items:
                action_text = el(
                    "p",
                    el("span", item.actor, class_="font-medium"),
                    raw(f" {item.action} "),
                    el(
                        "span",
                        item.resource,
                        class_="font-medium text-primary-600 dark:text-primary-400",
                    ),
                    raw(f" {item.resource_id}" if item.resource_id else ""),
                    class_="text-sm text-gray-700 dark:text-gray-300 leading-snug",
                )
                ts_el = (
                    el(
                        "p",
                        item.timestamp,
                        class_="text-xs text-gray-400 dark:text-gray-500 mt-0.5",
                    )
                    if item.timestamp
                    else ""
                )
                detail_el = el("div", action_text, ts_el, class_="flex-1 min-w-0")
                icon_span = raw(
                    f'<span class="flex-shrink-0 mt-0.5 w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center"><i data-lucide="{item.icon}" class="w-3.5 h-3.5 text-gray-500 dark:text-gray-400"></i></span>'
                )
                rows.append(
                    el(
                        "li",
                        icon_span,
                        detail_el,
                        class_="flex items-start gap-3 py-3 border-b border-gray-50 dark:border-gray-700/50 last:border-0",
                    )
                )
            body = el("ul", *rows, class_="divide-y-0")

        header_el = el(
            "div", *header_children, class_="flex items-center justify-between mb-4"
        )
        return el(
            "div",
            header_el,
            body,
            class_="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-5",
        )


# ---------------------------------------------------------------------------
# SystemHealthWidget component
# ---------------------------------------------------------------------------


class SystemHealthWidget(Component):
    """At-a-glance health status for backend services.

    Args:
        entries: List of :class:`HealthEntry` items.
        title: Card heading.
    """

    def __init__(
        self, entries: list[HealthEntry], *, title: str = "System Health"
    ) -> None:
        super().__init__()
        self.entries = entries
        self.title = title

    def render(self) -> Any:
        rows = []
        for entry in self.entries:
            status_color = _HEALTH_COLORS.get(entry.status, _HEALTH_COLORS["ok"])
            dot_color = _HEALTH_DOT.get(entry.status, _HEALTH_DOT["ok"])
            latency_html = (
                f'<span class="text-xs text-gray-400 dark:text-gray-500">{entry.latency_ms}ms</span>'
                if entry.latency_ms is not None
                else ""
            )
            status_label = entry.status.upper()
            left = el(
                "div",
                raw(
                    f'<span class="w-2 h-2 rounded-full {dot_color} flex-shrink-0"></span>'
                ),
                el(
                    "span",
                    entry.name,
                    class_="text-sm text-gray-700 dark:text-gray-300",
                ),
                class_="flex items-center gap-2",
            )
            right = el(
                "div",
                raw(latency_html),
                el(
                    "span", status_label, class_=f"text-xs font-semibold {status_color}"
                ),
                class_="flex items-center gap-2",
            )
            rows.append(
                el(
                    "li",
                    left,
                    right,
                    class_="flex items-center justify-between py-2.5 border-b border-gray-50 dark:border-gray-700/50 last:border-0",
                )
            )

        body = (
            el("ul", *rows, class_="divide-y-0")
            if rows
            else el(
                "p",
                "No services configured.",
                class_="text-sm text-gray-400 dark:text-gray-500",
            )
        )
        return el(
            "div",
            el(
                "h3",
                self.title,
                class_="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-4",
            ),
            body,
            class_="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-5",
        )


__all__ = [
    "ActivityFeed",
    "ActivityItem",
    "HealthEntry",
    "Stat",
    "StatCard",
    "StatCardGrid",
    "SystemHealthWidget",
]
