"""Management pages for relay request logs and usage rankings.

Pages are instantiated by the admin runtime from dotted-path handlers;
dependencies (the usage service) are resolved from the DI container by
protocol.  Every page renders metadata only — never prompts, media, or
headers — and shows an explicit unavailable state when the service is
missing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.admin import PageContent, PaginationContent
from lexigram.contracts.admin.widget_content import (
    EmptyContent,
    TableCell,
    TableContent,
)
from lexigram.contracts.ai.relay import (
    RelayModelRank,
    RelayRequestLogEntry,
)
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.ai.relay import RelayUsageServiceProtocol

__all__ = ["RelayRequestLogsPage", "RelayUsageRankingsPage"]

logger = get_logger(__name__)

_DEFAULT_DAYS = 7
_PAGE_SIZE = 20
_RANK_LIMIT = 10


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


def _unavailable_content(title: str, reason: str) -> PageContent:
    """Build a page with an explicit unavailable dependency state."""
    return PageContent(
        title=title,
        body=EmptyContent(
            title="Unavailable",
            message=reason,
            icon="alert-triangle",
        ),
    )


def _log_rows(entries: list[RelayRequestLogEntry]) -> list[tuple[Any, ...]]:
    """Build table rows for request-log entries."""
    rows: list[tuple[Any, ...]] = []
    for entry in entries:
        rows.append(
            (
                entry.request_id,
                entry.user_id or "-",
                entry.token_id or "-",
                entry.model or "-",
                f"{entry.prompt_tokens:,} / {entry.completion_tokens:,}",
                entry.cost,
                f"{entry.latency_ms}ms",
                entry.status,
                entry.error_code or "-",
            )
        )
    return rows


def _rank_rows(ranks: list[RelayModelRank]) -> list[tuple[Any, ...]]:
    """Build table rows for per-model usage rankings."""
    rows: list[tuple[Any, ...]] = []
    for rank in ranks:
        rows.append(
            (
                rank.model or "-",
                f"{rank.completion_tokens:,}",
                str(rank.request_count),
                rank.cost,
            )
        )
    return rows


class RelayRequestLogsPage:
    """Management page at /admin/ai-governance/relay-logs."""

    def __init__(self, service: RelayUsageServiceProtocol | None = None) -> None:
        self._service = service

    async def handle(self, request: Any) -> PageContent:
        """Render a paginated, filterable request-log list.

        Args:
            request: The starlette request.

        Returns:
            The structured request-log list page content.
        """
        if self._service is None:
            return _unavailable_content(
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
            return _unavailable_content("Request Logs", str(exc))

        if not entries:
            return PageContent(
                title="Request Logs",
                body=EmptyContent(
                    title="No request logs in this window.",
                    icon="inbox",
                ),
            )
        return PageContent(
            title="Request Logs",
            body=TableContent(
                columns=(
                    "Request",
                    "User",
                    "Token",
                    "Model",
                    "Tokens (p/c)",
                    "Cost",
                    "Latency",
                    "Status",
                    "Error",
                ),
                rows=tuple(
                    tuple(TableCell(str(cell)) for cell in row)
                    for row in _log_rows(entries)
                ),
            ),
            pagination=PaginationContent(
                page=page,
                total=len(entries),
                per_page=page_size,
                base_url=str(request.url).split("?")[0],
            ),
        )


class RelayUsageRankingsPage:
    """Management page at /admin/ai-governance/relay-rankings."""

    def __init__(self, service: RelayUsageServiceProtocol | None = None) -> None:
        self._service = service

    async def handle(self, request: Any) -> PageContent:
        """Render per-model token/cost rankings for the window.

        Args:
            request: The starlette request.

        Returns:
            The structured usage rankings page content.
        """
        if self._service is None:
            return _unavailable_content(
                "Usage Rankings",
                "Rankings require the relay usage service.",
            )
        days, _, _, _, _ = _params(request)
        try:
            ranks = await self._service.model_rank(days=days, limit=_RANK_LIMIT)
        except ValueError as exc:
            logger.warning("governance.rankings.window_rejected", error=str(exc))
            return _unavailable_content("Usage Rankings", str(exc))

        if not ranks:
            return PageContent(
                title="Usage Rankings",
                body=EmptyContent(
                    title="No usage in this window.",
                    icon="inbox",
                ),
            )
        return PageContent(
            title="Usage Rankings",
            body=TableContent(
                columns=("Model", "Completion Tokens", "Requests", "Cost"),
                rows=tuple(
                    tuple(TableCell(str(cell)) for cell in row)
                    for row in _rank_rows(ranks)
                ),
            ),
        )
