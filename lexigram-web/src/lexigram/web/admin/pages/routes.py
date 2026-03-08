from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.logging import get_logger
from lexigram.ui import Badge, Divider, EmptyState, el, render_to_string
from lexigram.ui.atoms.badge import BadgeVariant
from lexigram.web.routing.registry import RouteRegistry

logger = get_logger(__name__)


class WebRoutesPage:
    """Route listing page for /admin/web/routes."""

    def __init__(self, route_registry: RouteRegistry | None = None) -> None:
        self._route_registry = route_registry

    async def handle(self, request: Any) -> HTMLResponse:
        if self._route_registry is None:
            html = render_to_string(
                EmptyState(
                    title="Route Registry Unavailable",
                    message="The route registry could not be resolved. No routes to display.",
                    icon="map",
                ),
            )
            return HTMLResponse(html)

        try:
            routes = self._route_registry.get_all_routes()
        except Exception as exc:
            logger.warning("web_routes.fetch_failed", error=str(exc))
            html = render_to_string(
                EmptyState(
                    title="Route Registry Unavailable",
                    message=f"Failed to fetch routes: {exc}",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        Badge(method, variant=_method_variant(method)),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        path,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)] font-mono",
                    ),
                    el(
                        "td",
                        info.get("summary") or info.get("handler_name", ""),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        (
                            f"{info.get('controller').__name__}.{info.get('handler_name', '')}"
                            if info.get("controller")
                            else info.get("handler_name", "")
                        ),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)] font-mono",
                    ),
                )
            )
            for path, methods in routes.items()
            for method, info in methods.items()
        )

        if not rows:
            html = render_to_string(
                EmptyState(
                    title="No Routes Registered",
                    message="No routes have been registered yet.",
                    icon="map",
                ),
            )
            return HTMLResponse(html)

        html = render_to_string(
            el(
                "div",
                el(
                    "h1", "Routes", class_="text-2xl font-bold text-[var(--foreground)]"
                ),
                el(
                    "p",
                    "View all registered HTTP routes and their handlers.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                el(
                    "div",
                    el(
                        "table",
                        el(
                            "thead",
                            el(
                                "tr",
                                el(
                                    "th",
                                    "Method",
                                    style="width:15%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Path",
                                    style="width:35%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Name",
                                    style="width:25%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Handler",
                                    style="width:25%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                            ),
                        ),
                        el("tbody", rows, class_="divide-y divide-[var(--border)]"),
                        class_="min-w-full table-fixed divide-y divide-[var(--border)]",
                    ),
                    class_="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)]",
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)


def _method_variant(method: str) -> BadgeVariant:
    mapping: dict[str, BadgeVariant] = {
        "GET": "success",
        "POST": "primary",
        "PUT": "info",
        "PATCH": "warning",
        "DELETE": "danger",
        "HEAD": "gray",
        "OPTIONS": "gray",
    }
    return mapping.get(method.upper(), "default")
