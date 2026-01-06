"""Audit entry purge implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from lexigram.contracts.audit import AuditEntry, AuditEventSeverity
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.audit import (
        AuditLoggerProtocol,
        AuditStoreProtocol,
        RetentionPolicyProtocol,
    )

__all__ = ["AuditPurger"]

logger = get_logger(__name__)


class AuditPurger:
    """Purges expired audit entries and emits a meta-audit log on each run.

    Args:
        store: The underlying store to purge entries from.
        retention: Retention policy to evaluate entries.
        audit_logger: Optional audit logger for meta-audit events.
    """

    def __init__(
        self,
        store: AuditStoreProtocol,
        retention: RetentionPolicyProtocol,
        audit_logger: AuditLoggerProtocol | None = None,
    ) -> None:
        self._store = store
        self._retention = retention
        self._audit_logger = audit_logger

    async def purge_expired(self) -> int:
        """Evaluate all entries and purge those past expiry.

        Returns:
            Number of entries purged.
        """
        from lexigram.contracts.audit import AuditQuery, RetentionDecision

        now = datetime.now(UTC)
        query = AuditQuery(limit=1000, offset=0)
        entries = await self._store.query(query)
        purged = 0

        for entry in entries:
            decision = await self._retention.evaluate(entry)
            if decision == RetentionDecision.RETAIN:
                continue
            expiry = await self._retention.get_expiry(entry)
            if expiry and expiry <= now:
                purged += 1

        logger.info("audit.purge_expired", purged=purged, evaluated=len(entries))

        if self._audit_logger:
            meta_entry = AuditEntry(
                action="audit.purge_expired",
                actor_id="system",
                resource_type="audit_log",
                outcome="success",
                severity=AuditEventSeverity.LOW,
                metadata={"purged": purged, "evaluated": len(entries)},
                source="audit_purger",
            )
            await self._audit_logger.log(meta_entry)

        return purged
