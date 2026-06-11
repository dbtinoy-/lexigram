from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.data.sql.database import MigrationManagerProtocol
from lexigram.logging import get_logger
from lexigram.ui import Badge, Divider, EmptyState, el, raw, render_to_string

logger = get_logger(__name__)


class SqlMigrationsPage:
    def __init__(
        self,
        migration_manager: MigrationManagerProtocol | None = None,
    ) -> None:
        self._migration_manager = migration_manager

    async def handle(self, request: Any) -> HTMLResponse:
        if self._migration_manager is None:
            html = render_to_string(
                EmptyState(
                    title="Migrations Unavailable",
                    message="No migration manager is configured for this database.",
                    icon="arrow-up-circle",
                ),
            )
            return HTMLResponse(html)

        try:
            migrations = await self._migration_manager.get_applied_migrations()
        except Exception:
            html = render_to_string(
                EmptyState(
                    title="Error",
                    message="Failed to load migrations. Check the server logs for details.",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        if not migrations:
            html = render_to_string(
                EmptyState(
                    title="No Migrations",
                    message="No migrations have been applied yet.",
                    icon="arrow-up-circle",
                ),
            )
            return HTMLResponse(html)

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        m.version,
                        class_="px-4 py-3 whitespace-nowrap text-sm font-mono text-[var(--foreground)]",
                    ),
                    el("td", m.name, class_="px-4 py-3 whitespace-nowrap text-sm"),
                    el(
                        "td",
                        Badge(
                            "Applied" if m.success else "Failed",
                            variant="success" if m.success else "danger",
                        ),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                    el(
                        "td",
                        m.applied_at.isoformat() if m.applied_at else "",
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                )
            )
            for m in migrations
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Migrations",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Track applied database schema migrations.",
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
                                    "Version",
                                    style="width:20%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Name",
                                    style="width:30%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Status",
                                    style="width:20%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Applied At",
                                    style="width:30%",
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
