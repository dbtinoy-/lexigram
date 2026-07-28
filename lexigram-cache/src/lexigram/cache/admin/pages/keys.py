from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.ui import Card, Divider, EmptyState, el, render_to_string


class CacheKeysPage:
    """Key browser for /admin/cache/keys."""

    async def handle(self, request: Any) -> HTMLResponse:
        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Cache Keys",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Browse and manage stored cache keys.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Card(
                    title="Key Management",
                    content=render_to_string(
                        el(
                            "dl",
                            el(
                                "dt",
                                "Supported Operations",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                "Get, Set, Delete, Flush",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Key Pattern",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                "Backend-dependent (prefix/suffix conventions vary)",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "TTL Support",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                "Per-key expiration available",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            class_="divide-y divide-[var(--border)]",
                        )
                    ),
                ),
                el(
                    "div",
                    EmptyState(
                        title="No Keys Displayed",
                        message="Key enumeration is not supported by the current cache backend. Use the Flush Cache action to clear all keys.",
                        icon="key",
                    ),
                    class_="py-12",
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
