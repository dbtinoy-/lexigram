from __future__ import annotations

from typing import Any

from lexigram.contracts.admin import PageContent, PaginationContent
from lexigram.contracts.admin.widget_content import (
    EmptyContent,
    TableCell,
    TableContent,
)
from lexigram.contracts.audit import AuditLoggerProtocol, AuditQuery
from lexigram.logging import get_logger

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


class AuditLogPage:
    """Management page for /admin/audit."""

    def __init__(self, audit_logger: AuditLoggerProtocol | None = None) -> None:
        self._logger = audit_logger

    async def handle(self, request: Any) -> PageContent:
        if self._logger is None:
            return PageContent(
                title="Audit Log",
                body=EmptyContent(
                    title="Audit Log Unavailable",
                    message="The audit logger could not be resolved.",
                    icon="shield",
                ),
            )
        try:
            entries = await self._logger.query(AuditQuery(limit=MAX_FETCH))
        except Exception:
            logger.warning("audit_log.query_failed")
            entries = []

        if not entries:
            return PageContent(
                title="Audit Log",
                body=EmptyContent(
                    title="No Audit Entries",
                    message="No audit entries have been recorded yet.",
                    icon="shield-check",
                ),
            )

        total = len(entries)
        page, per_page = _paging(request)
        page = min(page, max(1, (total + per_page - 1) // per_page))
        offset = (page - 1) * per_page
        page_entries = entries[offset : offset + per_page]

        rows = tuple(
            (
                e.action,
                e.actor_id,
                f"{e.resource_type}/{e.resource_id}"
                if e.resource_id
                else e.resource_type,
                e.outcome,
                e.severity.value,
                e.occurred_at.strftime("%Y-%m-%d %H:%M") if e.occurred_at else "-",
                e.source or "-",
            )
            for e in page_entries
        )

        return PageContent(
            title="Audit Log",
            body=TableContent(
                columns=(
                    "Action",
                    "Actor",
                    "Resource",
                    "Outcome",
                    "Severity",
                    "Timestamp",
                    "Source",
                ),
                rows=tuple(tuple(TableCell(str(c)) for c in row) for row in rows),
            ),
            pagination=PaginationContent(
                page=page,
                total=total,
                per_page=per_page,
                base_url=str(request.url).split("?")[0],
            ),
        )
