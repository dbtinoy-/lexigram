"""Auth sessions management page — active session listing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.logging import get_logger
from lexigram.ui import Badge, Divider, EmptyState, el, raw, render_to_string

logger = get_logger(__name__)


class AuthSessionsPage:
    """Admin page listing active authentication sessions."""

    def __init__(
        self,
        session_repo: SessionRepositoryProtocol | None = None,
    ) -> None:
        self._session_repo = session_repo

    async def handle(self, request: Any) -> HTMLResponse:
        if self._session_repo is None:
            html = render_to_string(
                EmptyState(
                    title="Session Repository Unavailable",
                    message="No session repository is configured.",
                    icon="activity",
                ),
            )
            return HTMLResponse(html)

        try:
            sessions = await self._session_repo.find_active_by_user(
                user_id="*",
                cutoff=datetime.now(UTC),
            )
        except Exception:
            logger.warning("auth_sessions.list_failed")
            html = render_to_string(
                EmptyState(
                    title="Error",
                    message="Failed to retrieve sessions.",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        if not sessions:
            html = render_to_string(
                EmptyState(
                    title="No Active Sessions",
                    message="There are no active sessions.",
                    icon="activity",
                ),
            )
            return HTMLResponse(html)

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        s.get("session_id", "-"),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)] font-mono",
                    ),
                    el(
                        "td",
                        s.get("user_id", "-"),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        Badge("Active", variant="success"),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                    el(
                        "td",
                        str(s.get("expires_at", "")),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                )
            )
            for s in sessions
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Sessions",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Active user sessions across the platform.",
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
                                    "Session ID",
                                    style="width:30%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "User ID",
                                    style="width:30%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Status",
                                    style="width:16%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Expires",
                                    style="width:24%",
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
