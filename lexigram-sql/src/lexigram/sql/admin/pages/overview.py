from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.data.sql.database import (
    DatabaseProviderProtocol,
    MigrationManagerProtocol,
)
from lexigram.logging import get_logger
from lexigram.ui import (
    Card,
    Divider,
    EmptyState,
    Grid,
    StatCard,
    el,
    render_to_string,
)

logger = get_logger(__name__)


class SqlOverviewPage:
    def __init__(
        self,
        db: DatabaseProviderProtocol | None = None,
        migration_manager: MigrationManagerProtocol | None = None,
    ) -> None:
        self._db = db
        self._migration_manager = migration_manager

    async def handle(self, request: Any) -> HTMLResponse:
        if self._db is None:
            html = render_to_string(
                EmptyState(
                    title="Database Unavailable",
                    message="The database provider could not be resolved.",
                    icon="database",
                ),
            )
            return HTMLResponse(html)
        connected = False
        migration_count = 0
        try:
            async with self._db.scoped_context():
                connected = True
        except Exception:
            connected = False

        if self._migration_manager is not None:
            try:
                migrations = await self._migration_manager.get_applied_migrations()
                migration_count = len(migrations)
            except Exception:
                migration_count = 0

        provider_name = type(self._db).__name__

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "SQL Database",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Database connectivity, migration status, and query activity.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(
                        label="DB Status",
                        value="Connected" if connected else "Disconnected",
                        icon="database",
                        delta="OK" if connected else "DOWN",
                        delta_color="success" if connected else "danger",
                    ),
                    StatCard(
                        label="Migrations",
                        value=str(migration_count),
                        icon="arrow-up-circle",
                    ),
                    cols={"default": 1, "lg": 2},
                    gap=4,
                    class_="mb-6 mt-6",
                ),
                Card(
                    title="Database Details",
                    content=render_to_string(
                        el(
                            "dl",
                            el(
                                "dt",
                                "Database Provider",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                provider_name,
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Migration Count",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(migration_count),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Status",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                "Connected" if connected else "Disconnected",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            class_="divide-y divide-[var(--border)]",
                        ),
                    ),
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
