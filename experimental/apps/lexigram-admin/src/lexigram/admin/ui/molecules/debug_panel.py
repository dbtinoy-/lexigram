"""Debug Panel molecule for Lexigram Admin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.di.decorators import inject
from lexigram.ui import Component, el

if TYPE_CHECKING:
    from lexigram.admin.services.htmx_perf import HTMXPerformanceMonitor


@inject
class DebugPanel(Component):
    """A slide-over or collapsible panel for performance debugging."""

    def __init__(
        self,
        monitor: HTMXPerformanceMonitor,
        admin_prefix: str = "/admin",
        csrf_token: str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.monitor = monitor
        self.admin_prefix = admin_prefix.rstrip("/") or "/admin"
        self.csrf_token = csrf_token

    def render(self) -> Any:
        stats = self.monitor.get_stats()

        # Performance metrics
        metrics = [
            el(
                "div",
                el("span", "Total HTMX Requests: ", class_="font-medium"),
                el("span", str(stats.get("total_requests", 0))),
                class_="mb-1",
            ),
            el(
                "div",
                el("span", "Avg Duration: ", class_="font-medium"),
                el("span", f"{stats.get('avg_duration_ms', 0):.1f}ms"),
                class_="mb-1",
            ),
            el(
                "div",
                el("span", "Max Duration: ", class_="font-medium"),
                el("span", f"{stats.get('max_duration_ms', 0):.1f}ms"),
                class_="mb-1",
            ),
        ]

        # Slow requests list
        slow_list = []
        if stats.get("slow_requests"):
            slow_list.append(
                el(
                    "h4", "Slow Requests", class_="font-bold mt-4 mb-2 text-destructive"
                ),
            )
            for req in stats["slow_requests"]:
                slow_list.append(
                    el(
                        "div",
                        el(
                            "span",
                            f"{req['method']} {req['url']}",
                            class_="text-xs truncate block",
                        ),
                        el(
                            "span",
                            f"{req['duration_ms']:.1f}ms",
                            class_="text-xs font-bold",
                        ),
                        class_="p-2 bg-destructive/10 rounded mb-1",
                    ),
                )

        csrf_attrs = {}
        if self.csrf_token:
            from lexigram.serialization import dumps_str

            csrf_attrs["hx_headers"] = dumps_str(
                {"X-CSRF-Token": self.csrf_token}
            )

        return el(
            "div",
            el(
                "div",
                el("h3", "Lexigram Debug", class_="text-lg font-bold mb-4"),
                *metrics,
                *slow_list,
                el(
                    "button",
                    "Clear Stats",
                    hx_post=f"{self.admin_prefix}/debug/clear",
                    class_="mt-6 w-full py-2 bg-muted hover:bg-muted rounded text-sm transition-colors text-foreground",
                    **csrf_attrs,
                ),
                class_="p-6 h-full overflow-y-auto",
            ),
            id="debug-panel",
            class_="fixed right-0 top-0 bottom-0 w-80 bg-card shadow-2xl border-l border-border z-50 transform transition-transform",
            # We assume Alpine.js is present or using simple CSS/HTMX for toggle
            x_data="{ open: false }",
            x_show="open",
            # Toggle logic would be handled by a button elsewhere triggering 'open'
            **self.props,
        )
