"""Root event surface for lexigram-audit.

Defines domain events emitted by the audit subsystem (entry logged,
verification completed, retention purge).  Consumers subscribe via
:class:`~lexigram.contracts.events.protocols.EventBusProtocol`.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "AuditEntryLoggedEvent",
    "AuditPurgeCompletedEvent",
    "AuditVerificationCompletedEvent",
]


@dataclass(frozen=True, kw_only=True)
class AuditEntryLoggedEvent(DomainEvent):
    """Emitted when a new audit entry is persisted.

    Attributes:
        action: Dot-notation action identifier (e.g. ``"user.update"``).
        actor_id: ID of the user or service that performed the action.
        severity: Severity level string (e.g. ``"high"``).
    """

    action: str
    actor_id: str
    severity: str = "medium"


@dataclass(frozen=True, kw_only=True)
class AuditVerificationCompletedEvent(DomainEvent):
    """Emitted when an audit trail verification run completes.

    Attributes:
        entries_checked: Number of entries verified.
        mismatches_found: Number of checksum mismatches detected.
    """

    entries_checked: int
    mismatches_found: int = 0


@dataclass(frozen=True, kw_only=True)
class AuditPurgeCompletedEvent(DomainEvent):
    """Emitted when a retention-based purge run completes.

    Attributes:
        entries_purged: Number of entries deleted.
        entries_archived: Number of entries moved to cold storage.
    """

    entries_purged: int
    entries_archived: int = 0
