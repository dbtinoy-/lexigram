"""Management pages for relay request logs and usage rankings.

Pages are instantiated by the admin runtime from dotted-path handlers;
dependencies (the usage service) are resolved from the DI container by
protocol.  Every page renders metadata only — never prompts, media, or
headers — and shows an explicit unavailable state when the service is
missing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.responses import HTMLResponse

from lexigram.contracts.ai.relay import (
    RelayModelRank,
    RelayRequestLogEntry,
)
from lexigram.logging import get_logger
from lexigram.ui import Card, Divider, StatCard, el, render_to_string

if TYPE_CHECKING:
    from lexigram.contracts.ai.relay import RelayUsageServiceProtocol

__all__ = ["RelayRequestLogsPage", "RelayUsageRankingsPage"]

logger = get_logger(__name__)

_DEFAULT_DAYS = 7
_PAGE_SIZE = 20
_RANK_LIMIT = 10

_STATUS_COLORS = {
    "completed": "bg-green-100 text-green-700",
    "failed": "bg-red-100 text-red-700",
    "rate_limited": "bg-yellow-100 text-yellow-700",
    "unauthorized": "bg-orange-100 text-orange-700",
    "cancelled": "bg-gray-100 text-gray-500",
}


def _as_int(value: object, default: int, *, minimum: int) -> int:
    """Parse *value* as an integer, falling back on failure."""
    if not isinstance(value, str):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, parsed)


def _params(request: Any) -> tuple[int, int, int, str | None, str | None]:
    """Extract window, pagination, and filter parameters from a request."""
    raw = getattr(request, "query_params", {})
    days = _as_int(raw.get("days"), _DEFAULT_DAYS, minimum=1)
    page = _as_int(raw.get("page"), 1, minimum=1)
    page_size = _as_int(raw.get("page_size"), _PAGE_SIZE, minimum=1)
    user_id = raw.get("user")
    token_id = raw.get("token")
    return days, page, page_size, user_id, token_id


def _status_badge(status: str) -> Any:
    """Render a colored status badge for a request-log entry."""
    return el(
        "span",
        status,
        class_=(
            f"inline-block px-2 py-0.5 rounded text-xs font-medium "
            f"{_STATUS_COLORS.get(status, 'bg-gray-100 text-gray-500')}"
        ),
    )


def _table(headers: list[str], rows: list[Any]) -> Any:
    """Build a styled table element."""
    return el(
        "table",
        el(
            "thead",
            el(
                "tr",
                *[
                    el(
                        "th",
                        header,
                        class_=(
                            "text-left text-xs font-semibold "
                            "text-[var(--muted-foreground)] uppercase tracking-wider "
                            "pb-1 pr-3"
                        ),
                        scope_="col",
                    )
                    for header in headers
                ],
            ),
        ),
        el("tbody", *rows, class_="divide-y divide-[var(--border)]"),
        class_="w-full",
    )


def _unavailable_page(title: str, reason: str) -> HTMLResponse:
    """Render a full page with an explicit unavailable dependency card."""
    html = render_to_string(
        el(
            "div",
            el(
                "h1",
                title,
                class_="text-2xl font-bold text-[var(--foreground)]",
            ),
            Divider(),
            Card(
                title="Unavailable",
                content=render_to_string(
                    el(
                        "p",
                        reason,
                        class_="text-sm text-[var(--muted-foreground)] py-4",
                    )
                ),
                class_="border-yellow-300 bg-yellow-50",
            ),
        )
    )
    return HTMLResponse(html)


def _log_rows(entries: list[RelayRequestLogEntry]) -> list[Any]:
    """Build table rows for request-log entries."""
    rows: list[Any] = []
    for entry in entries:
        rows.append(
            el(
                "tr",
                el(
                    "td",
                    entry.request_id,
                    class_="py-1.5 pr-3 font-mono text-xs",
                ),
                el("td", entry.user_id or "-", class_="py-1.5 pr-3"),
                el("td", entry.token_id or "-", class_="py-1.5 pr-3"),
                el("td", entry.model or "-", class_="py-1.5 pr-3"),
                el(
                    "td",
                    f"{entry.prompt_tokens:,} / {entry.completion_tokens:,}",
                    class_="py-1.5 pr-3",
                ),
                el("td", entry.cost, class_="py-1.5 pr-3"),
                el(
                    "td",
                    f"{entry.latency_ms}ms",
                    class_="py-1.5 pr-3",
                ),
                el("td", _status_badge(entry.status), class_="py-1.5 pr-3"),
                el("td", entry.error_code or "-", class_="py-1.5"),
            )
        )
    return rows


def _rank_rows(ranks: list[RelayModelRank]) -> list[Any]:
    """Build table rows for per-model usage rankings."""
    rows: list[Any] = []
    for rank in ranks:
        rows.append(
            el(
                "tr",
                el("td", rank.model or "-", class_="py-1.5 pr-3"),
                el(
                    "td",
                    f"{rank.completion_tokens:,}",
                    class_="py-1.5 pr-3",
                ),
                el("td", str(rank.request_count), class_="py-1.5 pr-3"),
                el("td", rank.cost, class_="py-1.5"),
            )
        )
    return rows


class RelayRequestLogsPage:
    """Management page at /admin/ai-governance/relay-logs."""

    def __init__(self, service: RelayUsageServiceProtocol | None = None) -> None:
        self._service = service

    async def handle(self, request: Any) -> HTMLResponse:
        """Render a paginated, filterable request-log list.

        Args:
            request: The starlette request.

        Returns:
            The rendered request-log list page HTML.
        """
        if self._service is None:
            return _unavailable_page(
                "Request Logs",
                "Request logs require the relay usage service.",
            )
        days, page, page_size, user_id, token_id = _params(request)
        try:
            entries = await self._service.list_requests(
                days=days,
                page=page,
                page_size=page_size,
                user_id=user_id,
                token_id=token_id,
            )
        except ValueError as exc:
            logger.warning("governance.logs.window_rejected", error=str(exc))
            return _unavailable_page("Request Logs", str(exc))

        filter_line = "tracking metadata per dispatch"
        if user_id or token_id:
            filter_line = f"filtered by {(user_id and f'user {user_id} ') or ''}{(token_id and f'token {token_id}') or ''}".strip()
        table = (
            _table(
                [
                    "Request",
                    "User",
                    "Token",
                    "Model",
                    "Tokens (p/c)",
                    "Cost",
                    "Latency",
                    "Status",
                    "Error",
                ],
                _log_rows(entries),
            )
            if entries
            else el(
                "p",
                "No request logs in this window.",
                class_="text-sm text-[var(--muted-foreground)] py-4",
            )
        )
        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Request Logs",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    (
                        f"{filter_line} · last {days} days · "
                        f"page {page} of {page_size}-row pages"
                    ),
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Card(
                    title=f"Dispatches (last {days}d)",
                    content=render_to_string(table),
                ),
                el("div", class_="p-6"),
            )
        )
        return HTMLResponse(html)


class RelayUsageRankingsPage:
    """Management page at /admin/ai-governance/relay-rankings."""

    def __init__(self, service: RelayUsageServiceProtocol | None = None) -> None:
        self._service = service

    async def handle(self, request: Any) -> HTMLResponse:
        """Render per-model token/cost rankings for the window.

        Args:
            request: The starlette request.

        Returns:
            The rendered usage rankings page HTML.
        """
        if self._service is None:
            return _unavailable_page(
                "Usage Rankings",
                "Rankings require the relay usage service.",
            )
        days, _, _, _, _ = _params(request)
        try:
            ranks = await self._service.model_rank(days=days, limit=_RANK_LIMIT)
        except ValueError as exc:
            logger.warning("governance.rankings.window_rejected", error=str(exc))
            return _unavailable_page("Usage Rankings", str(exc))

        total_tokens = sum(rank.completion_tokens for rank in ranks)
        table = (
            _table(
                ["Model", "Completion Tokens", "Requests", "Cost"],
                _rank_rows(ranks),
            )
            if ranks
            else el(
                "p",
                "No usage in this window.",
                class_="text-sm text-[var(--muted-foreground)] py-4",
            )
        )
        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Usage Rankings",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    f"Per-model completion tokens over the last {days} days.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                el(
                    "div",
                    StatCard(
                        label="Models",
                        value=str(len(ranks)),
                        icon="bar-chart",
                    ),
                    StatCard(
                        label="Completion Tokens",
                        value=f"{total_tokens:,}",
                        icon="cpu",
                    ),
                    class_="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6",
                ),
                Card(
                    title=f"Model Rankings (last {days}d)",
                    content=render_to_string(table),
                ),
                el("div", class_="p-6"),
            )
        )
        return HTMLResponse(html)
