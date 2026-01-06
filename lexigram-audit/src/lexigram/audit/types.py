"""Package-internal types for lexigram-audit.

Shared types (``AuditEntry``, ``AuditQuery``, ``RetentionPolicy``, etc.)
live in ``lexigram.contracts.audit.types``. This module defines types
internal to the audit package implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

__all__ = [
    "AuditStoreBackend",
    "PurgeResult",
    "VerificationResult",
]


class AuditStoreBackend(StrEnum):
    """Supported audit store backends."""

    MEMORY = "memory"
    SQL = "sql"


@dataclass(frozen=True)
class VerificationResult:
    """Summary of an audit trail verification run.

    Attributes:
        entries_checked: Total entries verified.
        mismatches: Number of tampered entries detected.
        started_at: When the verification began.
        completed_at: When the verification finished.
    """

    entries_checked: int
    mismatches: int
    started_at: datetime
    completed_at: datetime

    @property
    def is_clean(self) -> bool:
        """True when no mismatches were detected."""
        return self.mismatches == 0


@dataclass(frozen=True)
class PurgeResult:
    """Summary of a retention-based purge run.

    Attributes:
        entries_purged: Number of entries deleted.
        entries_archived: Number of entries moved to cold storage.
        entries_retained: Number of entries kept.
    """

    entries_purged: int
    entries_archived: int = 0
    entries_retained: int = 0
