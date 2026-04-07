"""Convenience query service for the audit trail (LXF-003)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from lexigram.contracts.audit import AuditEntry, AuditQuery

if TYPE_CHECKING:
    from lexigram.contracts.audit import AuditStoreProtocol

__all__ = ["AuditQueryService"]


class AuditQueryService:
    """Convenience methods for querying the audit trail.

    Wraps an ``AuditStoreProtocol`` with higher-level query patterns.
    """

    def __init__(self, store: AuditStoreProtocol) -> None:
        self._store = store

    async def query_by_tenant(
        self,
        tenant_id: str,
        since: datetime,
        until: datetime,
        actions: list[str] | None = None,
        limit: int = 1000,
    ) -> list[AuditEntry]:
        """Query audit entries for a specific tenant within a time window.

        Args:
            tenant_id: Tenant identifier to filter by.
            since: Start of the time window (inclusive).
            until: End of the time window (inclusive).
            actions: Optional list of action types to include.
            limit: Maximum entries to return (default 1000).

        Returns:
            List of matching entries, newest-first.
        """
        query = AuditQuery(
            tenant_id=tenant_id,
            since=since,
            until=until,
            limit=limit,
            offset=0,
        )
        results = await self._store.query(query)
        if actions:
            results = [e for e in results if e.action in actions]
        return results

    async def query_by_correlation(
        self,
        correlation_id: str,
    ) -> list[AuditEntry]:
        """Query audit entries by request correlation ID.

        Args:
            correlation_id: Correlation identifier to match.

        Returns:
            List of matching entries across all tenants and services.
        """
        query = AuditQuery(
            correlation_id=correlation_id,
            limit=1000,
            offset=0,
        )
        return await self._store.query(query)
