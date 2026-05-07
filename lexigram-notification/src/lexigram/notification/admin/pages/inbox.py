"""Inbox management page for /admin/notifications."""

from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.logging import get_logger
from lexigram.notification.inbox.service import InboxService
from lexigram.ui import (
    Card,
    Divider,
    Grid,
    PageSizeSelector,
    PaginationLinks,
    StatCard,
    Zones,
    el,
    render_to_string,
)

logger = get_logger(__name__)

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 200


def _query_int(request: Any, name: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(request.query_params.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(value, hi))


def _pagination_block(page: int, total: int, per_page: int, base_url: str) -> Any:
    if total <= 0:
        return ""
    total_pages = max(1, (total + per_page - 1) // per_page)
    start_item = (page - 1) * per_page + 1
    end_item = min(page * per_page, total)
    return el(
        "div",
        {
            "class": (
                "flex items-center justify-between border-t border-border "
                "bg-background px-4 py-3 mt-4"
            ),
        },
        el(
            "p",
            {
                "class": (
                    "text-[11px] uppercase tracking-wider "
                    "text-[var(--muted-foreground)] font-semibold"
                ),
            },
            "Showing ",
            el("span", {"class": "font-bold"}, str(start_item)),
            " to ",
            el("span", {"class": "font-bold"}, str(end_item)),
            " of ",
            el("span", {"class": "font-bold"}, str(total)),
            " results",
        ),
        el(
            "div",
            {"class": "flex items-center space-x-4"},
            PaginationLinks(
                page=page,
                total_pages=total_pages,
                per_page=per_page,
                base_url=base_url,
            ),
            PageSizeSelector(per_page=per_page, base_url=base_url),
        ),
    )


class NotificationsInboxPage:
    """Full inbox page with persisted notifications and mark-all-read.

    Args:
        inbox_service: Inbox service. When ``None`` the default
            in-memory service is used.
    """

    def __init__(self, inbox_service: InboxService | None = None) -> None:
        self._inbox_service = inbox_service or InboxService()

    async def handle(self, request: Any) -> HTMLResponse:
        """Handle request and render the inbox page.

        Args:
            request: The ASGI request.

        Returns:
            HTML response for the inbox page.
        """
        user = getattr(request, "user", None)
        user_id = getattr(user, "id", None) if user is not None else None

        try:
            raw_per_page = request.query_params.get("per_page") or request.query_params.get(
                "limit"
            )
            per_page = (
                int(raw_per_page)
                if raw_per_page is not None
                else DEFAULT_PER_PAGE
            )
        except (TypeError, ValueError):
            per_page = DEFAULT_PER_PAGE
        per_page = max(1, min(per_page, MAX_PER_PAGE))
        page = _query_int(request, "page", 1, 1, 10**6)

        if user_id is None:
            messages: list[Any] = []
            unread = 0
        else:
            try:
                messages = await self._inbox_service.get_inbox(user_id)
                unread = await self._inbox_service.count_unread(user_id)
            except Exception as exc:  # noqa: BLE001 — non-fatal page render
                logger.warning("inbox_page.load_failed", error=str(exc))
                messages = []
                unread = 0

        total = len(messages)
        page = min(page, max(1, (total + per_page - 1) // per_page))
        offset = (page - 1) * per_page
        page_messages = messages[offset : offset + per_page]

        items = [
            el(
                "div",
                {
                    "class": "flex items-start gap-3 px-4 py-3 border-b border-border",
                    "data-inbox-message": msg.id,
                },
                el(
                    "span",
                    {
                        "class": "mt-1.5 w-2 h-2 rounded-full flex-shrink-0 bg-success"
                        if msg.read
                        else "mt-1.5 w-2 h-2 rounded-full flex-shrink-0 bg-primary",
                    },
                ),
                el(
                    "div",
                    el(
                        "p",
                        {"class": "text-sm font-medium text-foreground"},
                        msg.title,
                    ),
                    el(
                        "p",
                        {"class": "text-xs text-muted-foreground mt-0.5"},
                        msg.body,
                    ),
                    el(
                        "p",
                        {"class": "text-xs text-muted-foreground/60 mt-1"},
                        msg.created_at.isoformat(),
                    ),
                    class_="flex-1 min-w-0",
                ),
            )
            for msg in page_messages
        ]

        content = render_to_string(
            el(
                "div",
                {"class": "p-6"},
                el(
                    "h1",
                    {"class": "text-2xl font-bold text-foreground"},
                    "Notifications",
                ),
                el(
                    "p",
                    {"class": "text-sm text-muted-foreground mt-1 mb-6"},
                    f"{unread} unread of {len(messages)} total",
                ),
                Divider(),
                Grid(
                    StatCard(
                        label="Unread",
                        value=str(unread),
                        icon="bell",
                        delta="ACTIVE" if unread else "CLEAR",
                        delta_color="danger" if unread else "success",
                    ),
                    StatCard(
                        label="Total Notifications",
                        value=str(len(messages)),
                        icon="inbox",
                    ),
                    cols={"default": 1, "lg": 2},
                    gap=4,
                    class_="mb-6 mt-6",
                ),
                el(
                    "div",
                    {"class": "flex items-center justify-end mb-4"},
                    el(
                        "button",
                        {
                            "hx-post": "/admin/notifications/read-all",
                            "hx-swap": "none",
                            "class": "text-sm text-primary-600 dark:text-primary-400 hover:underline",
                        },
                        "Mark all read",
                    ),
                ),
                el(
                    "div",
                    Card(
                        content=(
                            el("div", *items)
                            if items
                            else (
                                el(
                                    "div",
                                    {
                                        "class": "px-4 py-8 text-center text-sm text-muted-foreground",
                                    },
                                    "No notifications",
                                ),
                            )
                        ),
                    ),
                    _pagination_block(page, total, per_page, request.url.path),
                    id=Zones.DATA.id,
                ),
            ),
        )
        return HTMLResponse(content)
