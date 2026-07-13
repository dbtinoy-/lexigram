from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.audit import AuditLoggerProtocol, AuditQuery
from lexigram.logging import get_logger
from lexigram.ui import (
    Badge,
    Divider,
    EmptyState,
    Grid,
    PageSizeSelector,
    PaginationLinks,
    StatCard,
    Zones,
    el,
    raw,
    render_to_string,
)

logger = get_logger(__name__)

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 200
MAX_FETCH = 10_000


def _query_int(request: Any, name: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(request.query_params.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(value, hi))


def _paging(request: Any) -> tuple[int, int]:
    page = _query_int(request, "page", 1, 1, 10**6)
    per_page = _query_int(request, "per_page", DEFAULT_PER_PAGE, 1, MAX_PER_PAGE)
    return page, per_page


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


class AuditLogPage:
    """Management page for /admin/audit."""

    def __init__(self, audit_logger: AuditLoggerProtocol | None = None) -> None:
        self._logger = audit_logger

    async def handle(self, request: Any) -> HTMLResponse:
        if self._logger is None:
            html = render_to_string(
                EmptyState(
                    title="Audit Log Unavailable",
                    message="The audit logger could not be resolved.",
                    icon="shield",
                ),
            )
            return HTMLResponse(html)
        try:
            entries = await self._logger.query(AuditQuery(limit=MAX_FETCH))
        except Exception:
            logger.warning("audit_log.query_failed")
            entries = []

        total = len(entries)
        high = sum(1 for e in entries if e.severity.value in ("high", "critical"))

        page, per_page = _paging(request)
        page = min(page, max(1, (total + per_page - 1) // per_page))
        offset = (page - 1) * per_page
        page_entries = entries[offset : offset + per_page]

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        e.action,
                        class_="px-4 py-3 whitespace-nowrap text-sm font-mono text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        e.actor_id,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        f"{e.resource_type}/{e.resource_id}"
                        if e.resource_id
                        else e.resource_type,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                    el(
                        "td",
                        render_to_string(
                            Badge(
                                e.outcome,
                                variant="success"
                                if e.outcome == "success"
                                else "danger",
                            )
                        ),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                    el(
                        "td",
                        render_to_string(
                            Badge(
                                e.severity.value,
                                variant="danger"
                                if e.severity.value in ("high", "critical")
                                else "warning"
                                if e.severity.value == "medium"
                                else "default",
                            )
                        ),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                    el(
                        "td",
                        e.occurred_at.strftime("%Y-%m-%d %H:%M")
                        if e.occurred_at
                        else "-",
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                    el(
                        "td",
                        e.source or "-",
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                )
            )
            for e in page_entries
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Audit Log",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Browse and search audit trail entries.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(
                        label="Recent Entries",
                        value=str(total),
                        icon="shield-check",
                    ),
                    StatCard(
                        label="High/Critical",
                        value=str(high),
                        delta_color="red" if high > 0 else "green",
                        icon="alert-triangle",
                    ),
                    cols={"default": 1, "lg": 2},
                    gap=4,
                ),
                el(
                    "div",
                    el(
                        "h2",
                        "Recent Entries",
                        class_="text-lg font-semibold text-[var(--foreground)] mb-3 mt-6",
                    ),
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
                                        "Action",
                                        style="width:18%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                    el(
                                        "th",
                                        "Actor",
                                        style="width:15%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                    el(
                                        "th",
                                        "Resource",
                                        style="width:15%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                    el(
                                        "th",
                                        "Outcome",
                                        style="width:12%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                    el(
                                        "th",
                                        "Severity",
                                        style="width:10%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                    el(
                                        "th",
                                        "Timestamp",
                                        style="width:15%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                    el(
                                        "th",
                                        "Source",
                                        style="width:15%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                ),
                            ),
                            el(
                                "tbody",
                                raw(rows),
                                class_="divide-y divide-[var(--border)]",
                            ),
                            class_="min-w-full table-fixed divide-y divide-[var(--border)]",
                        ),
                        class_="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)]",
                    ),
                    _pagination_block(page, total, per_page, request.url.path),
                    id=Zones.DATA.id,
                    class_="mt-4",
                ),
                class_="p-6",
            ),
        )

        return HTMLResponse(html)
