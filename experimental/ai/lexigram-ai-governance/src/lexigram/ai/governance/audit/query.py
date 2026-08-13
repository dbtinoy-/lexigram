"""Governance audit query and streaming export service.

Provides rich query, aggregation, and streaming CSV/JSON export of
:class:`~lexigram.ai.governance.audit.models.AIAuditEvent` records stored
via any :class:`~lexigram.ai.governance.audit.store.AIAuditStore` implementation.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
import io
from typing import TYPE_CHECKING

from lexigram.ai.governance.audit.models import AIAuditEvent, AuditQuery, AuditSummary
from lexigram.logging import (
    get_logger,
)
from lexigram.serialization import dumps_str

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lexigram.ai.governance.audit.store import AIAuditStore

logger = get_logger(__name__)

_CSV_FIELDS = (
    "event_id",
    "event_type",
    "timestamp",
    "model",
    "provider",
    "user_id",
    "status",
    "tokens",
    "cost",
    "latency_ms",
    "metadata",
)

_EXPORT_PAGE_SIZE = 500


def _event_to_csv_row(event: AIAuditEvent) -> list[str]:
    """Serialise *event* to a flat list of strings suitable for a CSV row.

    Args:
        event: The audit event to serialise.

    Returns:
        Ordered list of string values matching :data:`_CSV_FIELDS`.
    """
    return [
        event.event_id,
        event.event_type.value,
        event.timestamp.isoformat(),
        event.model or "",
        event.provider or "",
        event.user_id or "",
        event.status,
        str(event.tokens) if event.tokens is not None else "",
        str(event.cost) if event.cost is not None else "",
        str(event.latency_ms) if event.latency_ms is not None else "",
        dumps_str(event.metadata),
    ]


class AuditQueryService:
    """Query and export governance audit records.

    All heavy pagination is handled internally so callers can use simple
    async-for loops over streaming export methods.

    Args:
        store: Audit store to delegate persistence operations to.
    """

    def __init__(self, store: AIAuditStore) -> None:
        self._store = store

    async def query(
        self,
        *,
        model: str | None = None,
        tenant_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[AIAuditEvent]:
        """Retrieve audit events matching the given filters.

        Args:
            model: Restrict to events for this model identifier.
            tenant_id: Restrict to events for this user/tenant ID.
            start: Inclusive lower bound on event timestamp (UTC).
            end: Inclusive upper bound on event timestamp (UTC).
            limit: Maximum number of results (default: 100, max: 1 000).

        Returns:
            Matching events ordered by timestamp descending.
        """
        q = AuditQuery(
            model=model,
            user_id=tenant_id,
            start=start,
            end=end,
            limit=min(limit, 1000),
        )
        logger.debug("audit_query", model=model, tenant_id=tenant_id, limit=limit)
        return await self._store.query(q)

    async def export_csv(self, query: AuditQuery) -> AsyncIterator[bytes]:
        """Stream audit records as CSV-encoded bytes.

        The first chunk contains the header row.  Subsequent chunks are
        batches of :data:`_EXPORT_PAGE_SIZE` rows.  All pages are fetched
        from the underlying store on demand so memory usage stays bounded.

        Args:
            query: Filter criteria; ``limit`` and ``offset`` are used for
                internal pagination and should be left at their defaults.

        Yields:
            UTF-8 encoded bytes for each batch (header + rows).
        """
        # Yield header
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(_CSV_FIELDS)
        yield buf.getvalue().encode()

        offset = 0
        page_query = AuditQuery(
            start=query.start,
            end=query.end,
            event_types=query.event_types,
            user_id=query.user_id,
            model=query.model,
            provider=query.provider,
            status=query.status,
            limit=_EXPORT_PAGE_SIZE,
            offset=offset,
        )

        while True:
            page_query.offset = offset
            events = await self._store.query(page_query)
            if not events:
                break

            buf = io.StringIO()
            writer = csv.writer(buf)
            for event in events:
                writer.writerow(_event_to_csv_row(event))
            yield buf.getvalue().encode()

            if len(events) < _EXPORT_PAGE_SIZE:
                break
            offset += _EXPORT_PAGE_SIZE

        logger.debug("audit_export_csv_complete", offset=offset)

    async def export_json(self, query: AuditQuery) -> AsyncIterator[bytes]:
        """Stream audit records as newline-delimited JSON (NDJSON).

        Each line is a complete JSON object representing one
        :class:`~lexigram.ai.governance.audit.models.AIAuditEvent`.

        Args:
            query: Filter criteria; ``limit`` and ``offset`` are used for
                internal pagination.

        Yields:
            UTF-8 encoded bytes for each page of NDJSON lines.
        """
        offset = 0
        page_query = AuditQuery(
            start=query.start,
            end=query.end,
            event_types=query.event_types,
            user_id=query.user_id,
            model=query.model,
            provider=query.provider,
            status=query.status,
            limit=_EXPORT_PAGE_SIZE,
            offset=offset,
        )

        while True:
            page_query.offset = offset
            events = await self._store.query(page_query)
            if not events:
                break

            lines: list[str] = []
            for event in events:
                record = {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "model": event.model,
                    "provider": event.provider,
                    "user_id": event.user_id,
                    "status": event.status,
                    "tokens": event.tokens,
                    "cost": event.cost,
                    "latency_ms": event.latency_ms,
                    "metadata": event.metadata,
                }
                lines.append(dumps_str(record))
            yield ("\n".join(lines) + "\n").encode()

            if len(events) < _EXPORT_PAGE_SIZE:
                break
            offset += _EXPORT_PAGE_SIZE

        logger.debug("audit_export_json_complete", offset=offset)

    async def summary(self, window_hours: int = 24) -> AuditSummary:
        """Aggregate audit statistics for the last *window_hours* hours.

        Args:
            window_hours: Look-back window in hours (default: 24).

        Returns:
            :class:`~lexigram.ai.governance.audit.models.AuditSummary` with
            total events, spend, tokens, denied count, and breakdowns by
            model, user, and event type.
        """
        start = datetime.now(UTC) - timedelta(hours=window_hours)
        q = AuditQuery(start=start, limit=0)
        logger.debug("audit_summary", window_hours=window_hours)
        return await self._store.aggregate(q)


__all__ = ["AuditQueryService"]
