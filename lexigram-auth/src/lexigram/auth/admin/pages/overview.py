"""Auth overview management page — user and session counts."""

from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.contracts.auth.store import UserStoreProtocol
from lexigram.logging import get_logger
from lexigram.ui import Card, Divider, Grid, StatCard, el, render_to_string

logger = get_logger(__name__)


class AuthOverviewPage:
    """Admin overview page for authentication stats."""

    def __init__(
        self,
        user_store: UserStoreProtocol | None = None,
        session_repo: SessionRepositoryProtocol | None = None,
    ) -> None:
        self._user_store = user_store
        self._session_repo = session_repo

    async def handle(self, request: Any) -> HTMLResponse:
        user_count: str | int = "N/A"
        session_count: str | int = "N/A"

        if self._user_store is not None:
            try:
                user_count = await self._user_store.count_users()
            except Exception:
                logger.warning("auth_overview.user_count_unavailable")

        if self._session_repo is not None:
            try:
                sessions = await self._session_repo.find_active_by_user(
                    user_id="*",
                    cutoff=None,
                )
                session_count = len(sessions)
            except Exception:
                session_count = "N/A"

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Authentication",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "User accounts, sessions, and token configuration.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(label="Total Users", value=str(user_count), icon="users"),
                    StatCard(
                        label="Active Sessions",
                        value=str(session_count),
                        icon="activity",
                    ),
                    cols={"default": 1, "lg": 2},
                    gap=4,
                    class_="mb-6 mt-6",
                ),
                Card(
                    title="Service Details",
                    content=render_to_string(
                        el(
                            "dl",
                            el(
                                "dt",
                                "User Store",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                "Configured"
                                if self._user_store is not None
                                else "Not configured",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Session Repository",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                "Configured"
                                if self._session_repo is not None
                                else "Not configured",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Total Registered Users",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(user_count),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Active Sessions",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(session_count),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            class_="divide-y divide-[var(--border)]",
                        )
                    ),
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
