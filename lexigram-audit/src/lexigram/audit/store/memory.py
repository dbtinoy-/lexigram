"""In-memory audit store for testing and development."""

from __future__ import annotations

from collections import deque
from datetime import datetime

from lexigram.contracts.audit import AuditEntry, AuditQuery

__all__ = ["InMemoryAuditStore"]


class InMemoryAuditStore:
    """In-memory audit store implementing AuditStoreProtocol.

    Uses a bounded deque. Thread-safe for single-event-loop async usage.

    Args:
        max_entries: Maximum capacity. Oldest entries dropped when full.
    """

    def __init__(self, max_entries: int = 10_000) -> None:
        self._entries: deque[AuditEntry] = deque(maxlen=max_entries)

    async def append(self, entry: AuditEntry) -> None:
        """Persist a single audit entry."""
        self._entries.append(entry)

    async def query(self, query: AuditQuery) -> list[AuditEntry]:
        """Retrieve entries matching filters, newest-first."""
        results: list[AuditEntry] = []
        for entry in reversed(self._entries):
            if query.actor_id is not None and entry.actor_id != query.actor_id:
                continue
            if query.action is not None and entry.action != query.action:
                continue
            if (
                query.resource_type is not None
                and entry.resource_type != query.resource_type
            ):
                continue
            if query.resource_id is not None and entry.resource_id != query.resource_id:
                continue
            if query.source is not None and entry.source != query.source:
                continue
            if query.severity is not None and entry.severity != query.severity:
                continue
            if query.outcome is not None and entry.outcome != query.outcome:
                continue
            if (
                query.correlation_id is not None
                and entry.correlation_id != query.correlation_id
            ):
                continue
            if query.tenant_id is not None and entry.tenant_id != query.tenant_id:
                continue
            if query.since is not None and entry.occurred_at < query.since:
                continue
            if query.until is not None and entry.occurred_at > query.until:
                continue
            results.append(entry)
            if len(results) >= query.offset + query.limit:
                break
        return results[query.offset : query.offset + query.limit]

    async def count(self, query: AuditQuery) -> int:
        """Return count of entries matching filters."""
        unlimited = AuditQuery(
            actor_id=query.actor_id,
            action=query.action,
            resource_type=query.resource_type,
            resource_id=query.resource_id,
            source=query.source,
            severity=query.severity,
            outcome=query.outcome,
            tenant_id=query.tenant_id,
            correlation_id=query.correlation_id,
            since=query.since,
            until=query.until,
            limit=1_000_000,
            offset=0,
        )
        return len(await self.query(unlimited))

    async def delete_expired(self, cutoff: datetime) -> int:
        """Delete entries whose stored expiry precedes or equals cutoff.

        Mirrors the SQL store: only entries stamped with the
        ``__expires_at`` metadata key are candidates for deletion.
        """
        expired: list[AuditEntry] = []
        for entry in self._entries:
            stamp = entry.metadata.get("__expires_at")
            if stamp is None:
                continue
            try:
                expires = datetime.fromisoformat(stamp)
            except (TypeError, ValueError):
                continue
            if expires <= cutoff:
                expired.append(entry)
        for entry in expired:
            self._entries.remove(entry)
        return len(expired)

    def clear(self) -> None:
        """Clear all entries (test helper)."""
        self._entries.clear()
