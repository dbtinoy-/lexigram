"""Auth tokens management page — token key information."""

from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.auth.authn.jwt import JWTTokenManager
from lexigram.logging import get_logger
from lexigram.ui import Badge, Card, Divider, EmptyState, el, raw, render_to_string

logger = get_logger(__name__)


class AuthTokensPage:
    """Admin page displaying JWT token configuration and key info."""

    def __init__(
        self,
        token_manager: JWTTokenManager | None = None,
    ) -> None:
        self._token_manager = token_manager

    async def handle(self, request: Any) -> HTMLResponse:
        if self._token_manager is None:
            html = render_to_string(
                EmptyState(
                    title="Token Manager Unavailable",
                    message="No JWT token manager is configured.",
                    icon="key",
                ),
            )
            return HTMLResponse(html)

        try:
            keys_data = self._token_manager.list_keys()
            current_key_id = self._token_manager.current_key_id
            algorithm = self._token_manager.algorithm
            access_exp = self._token_manager.access_expiration_hours
            refresh_exp = self._token_manager.refresh_expiration_days
        except Exception:
            logger.warning("auth_tokens.config_unavailable")
            html = render_to_string(
                EmptyState(
                    title="Token Configuration Unavailable",
                    message="Failed to read JWT token configuration.",
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
                        kid,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)] font-mono",
                    ),
                    el(
                        "td",
                        Badge(
                            "Current" if kid == current_key_id else "Active",
                            variant="success" if kid == current_key_id else "default",
                        ),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                    el(
                        "td",
                        str(meta.get("created_at", "-")),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                )
            )
            for kid, meta in keys_data.items()
        )

        table_section = ""
        if keys_data:
            table_section = el(
                "div",
                el("h2", "Signing Keys", class_="text-xl font-semibold mb-4"),
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
                                    "Key ID",
                                    style="width:40%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Status",
                                    style="width:25%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Created",
                                    style="width:35%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                            ),
                        ),
                        el("tbody", raw(rows), class_="divide-y divide-[var(--border)]"),
                        class_="min-w-full table-fixed divide-y divide-[var(--border)]",
                    ),
                    class_="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)]",
                ),
            )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Token Configuration",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "JWT signing keys, algorithms, and expiration settings.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Card(
                    title="JWT Settings",
                    content=render_to_string(
                        el(
                            "dl",
                            el(
                                "dt",
                                "Algorithm",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                algorithm,
                                class_="text-sm text-[var(--foreground)] pb-3 font-mono",
                            ),
                            el(
                                "dt",
                                "Access Token Expiration",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                f"{access_exp} hours",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Refresh Token Expiration",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                f"{refresh_exp} days",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Current Key ID",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                current_key_id,
                                class_="text-sm text-[var(--foreground)] pb-3 font-mono",
                            ),
                            class_="divide-y divide-[var(--border)]",
                        ),
                    ),
                ),
                table_section,
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
