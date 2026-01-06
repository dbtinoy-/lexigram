"""Auth users management page — list registered users."""

from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.auth.store import UserStoreProtocol
from lexigram.logging import get_logger
from lexigram.ui import Badge, Divider, EmptyState, el, render_to_string

logger = get_logger(__name__)


class AuthUsersPage:
    """Admin page listing registered auth users."""

    def __init__(
        self,
        user_store: UserStoreProtocol | None = None,
    ) -> None:
        self._user_store = user_store

    async def handle(self, request: Any) -> HTMLResponse:
        if self._user_store is None:
            html = render_to_string(
                EmptyState(
                    title="User Store Unavailable",
                    message="No user store is configured.",
                    icon="users",
                ),
            )
            return HTMLResponse(html)

        try:
            users = await self._user_store.list_users()
        except Exception:
            logger.warning("auth_users.list_users_failed")
            html = render_to_string(
                EmptyState(
                    title="User Store Error",
                    message="Failed to retrieve users from the store.",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        if not users:
            html = render_to_string(
                EmptyState(
                    title="No Users Found",
                    message="There are no registered users yet.",
                    icon="users",
                ),
            )
            return HTMLResponse(html)

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        u.user_id,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)] font-mono",
                    ),
                    el(
                        "td",
                        getattr(u, "email", "-"),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        Badge(
                            "Active" if getattr(u, "is_active", True) else "Inactive",
                            variant="success"
                            if getattr(u, "is_active", True)
                            else "danger",
                        ),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                )
            )
            for u in users
        )

        html = render_to_string(
            el(
                "div",
                el("h1", "Users", class_="text-2xl font-bold text-[var(--foreground)]"),
                el(
                    "p",
                    "Manage registered user accounts and their status.",
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
                                    "ID",
                                    style="width:40%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Email",
                                    style="width:40%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Status",
                                    style="width:20%",
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
