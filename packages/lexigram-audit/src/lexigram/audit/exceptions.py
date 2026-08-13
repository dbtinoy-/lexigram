"""Exception hierarchy for the lexigram-audit package.

All audit exceptions inherit from ``lexigram.contracts.exceptions.domain.DomainError``
and are expected, recoverable failures.
"""

from __future__ import annotations

from lexigram.contracts.exceptions.domain import DomainError


class AuditError(DomainError):
    """Base exception for all audit-domain errors."""

    _code = "LEX_ERR_AUDIT_001"


class AuditStoreError(AuditError):
    """Raised when the audit store fails to persist or query entries."""

    _code = "LEX_ERR_AUDIT_002"


class AuditVerificationError(AuditError):
    """Raised when audit trail verification encounters an unexpected failure."""

    _code = "LEX_ERR_AUDIT_003"


class AuditRetentionError(AuditError):
    """Raised when a retention purge fails."""

    _code = "LEX_ERR_AUDIT_004"
