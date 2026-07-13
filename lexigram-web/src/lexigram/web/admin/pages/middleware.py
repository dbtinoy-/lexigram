from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.logging import get_logger
from lexigram.ui import Divider, EmptyState, el, raw, render_to_string
from lexigram.web.middleware.base import MiddlewareRegistry
from lexigram.web.middleware.registry import MiddlewareAdapterRegistry

logger = get_logger(__name__)


class WebMiddlewarePage:
    """Middleware overview page for /admin/web/middleware."""

    def __init__(
        self,
        middleware_registry: MiddlewareRegistry | None = None,
        adapter_registry: MiddlewareAdapterRegistry | None = None,
    ) -> None:
        self._middleware_registry = middleware_registry
        self._adapter_registry = adapter_registry

    async def handle(self, request: Any) -> HTMLResponse:
        if self._middleware_registry is None:
            html = render_to_string(
                EmptyState(
                    title="Middleware Registry Unavailable",
                    message="The middleware registry could not be resolved.",
                    icon="layers",
                ),
            )
            return HTMLResponse(html)

        try:
            names = self._middleware_registry.get_middleware_order()
            stack = getattr(self._middleware_registry, "_middleware_stack", [])
        except Exception as exc:
            logger.warning("web_middleware.list_failed", error=str(exc))
            names = []
            stack = []

        if not names:
            html = render_to_string(
                EmptyState(
                    title="No Middleware Registered",
                    message="No middleware has been registered yet.",
                    icon="layers",
                ),
            )
            return HTMLResponse(html)

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        name,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        cls.__name__,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)] font-mono",
                    ),
                    el(
                        "td",
                        cls.__module__,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                ),
            )
            for (_, cls, _), name in zip(stack, names, strict=True)
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Middleware",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Manage the HTTP middleware pipeline.",
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
                                    "Name",
                                    style="width:25%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Class",
                                    style="width:30%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Module",
                                    style="width:45%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                            ),
                        ),
                        el("tbody", raw(rows), class_="divide-y divide-[var(--border)]"),
                        class_="min-w-full table-fixed divide-y divide-[var(--border)]",
                    ),
                    class_="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)]",
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
