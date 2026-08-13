"""Fire-tolerant audit logger wrapping an AuditStoreProtocol."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.audit import AuditEntry, AuditQuery, AuditStoreProtocol
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.audit import RetentionPolicyProtocol

__all__ = ["AuditLogger"]

logger = get_logger(__name__)


class AuditLogger:
    """Core audit logger implementing AuditLoggerProtocol.

    Fire-tolerant: ``log()`` catches all exceptions and emits a warning.
    Audit failure must never block the operation that triggered it.

    Args:
        store: Underlying storage backend (AuditStoreProtocol).
        retention: Optional retention policy for computing entry expiry.
    """

    def __init__(
        self,
        store: AuditStoreProtocol,
        retention: RetentionPolicyProtocol | None = None,
    ) -> None:
        self._store = store
        self._retention = retention

    async def log(self, entry: AuditEntry) -> None:
        """Record an audit entry. Never raises.

        Args:
            entry: The audit event to persist.
        """
        try:
            final_entry = entry
            if self._retention is not None:
                expires_at = await self._retention.get_expiry(entry)
                if expires_at is not None:
                    import dataclasses

                    final_entry = dataclasses.replace(
                        entry,
                        metadata={
                            **entry.metadata,
                            "__expires_at": expires_at.isoformat(),
                        },
                    )
            await self._store.append(final_entry)
        except Exception as exc:
            logger.warning(
                "audit.log_failed",
                action=entry.action,
                actor_id=entry.actor_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    async def query(self, query: AuditQuery) -> list[AuditEntry]:
        """Query entries matching filters. Returns empty list on error.

        Args:
            query: Filter criteria encapsulated in an AuditQuery object.

        Returns:
            List of matching entries, newest-first.
        """
        try:
            return await self._store.query(query)
        except Exception as exc:
            logger.warning(
                "audit.query_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return []
