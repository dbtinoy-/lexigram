"""Policy-based retention evaluation for audit entries."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from lexigram.contracts.audit import AuditEntry, RetentionDecision

if TYPE_CHECKING:
    from lexigram.contracts.audit import RetentionPolicy

__all__ = ["PolicyBasedRetention"]


class PolicyBasedRetention:
    """Evaluates retention policies to determine entry expiry.

    Implements RetentionPolicyProtocol.

    Args:
        policy: Retention policy configuration.
    """

    def __init__(self, policy: RetentionPolicy) -> None:
        self._policy = policy

    async def evaluate(self, entry: AuditEntry) -> RetentionDecision:
        """Determine retention decision based on severity and source.

        Args:
            entry: The audit entry to evaluate.

        Returns:
            RetentionDecision.RETAIN if indefinite, RETAIN_UNTIL otherwise.
        """
        retention_days = self._get_retention_days(entry)
        if retention_days <= 0:
            return RetentionDecision.RETAIN
        return RetentionDecision.RETAIN_UNTIL

    async def get_expiry(self, entry: AuditEntry) -> datetime | None:
        """Return expiry datetime for an entry, or None for indefinite retention.

        Args:
            entry: The audit entry to evaluate.

        Returns:
            UTC expiry datetime, or None.
        """
        retention_days = self._get_retention_days(entry)
        if retention_days <= 0:
            return None
        return entry.occurred_at + timedelta(days=retention_days)

    def _get_retention_days(self, entry: AuditEntry) -> int:
        """Resolve retention days: severity override → source override → default."""
        severity_key = entry.severity.value
        if severity_key in self._policy.severity_overrides:
            return self._policy.severity_overrides[severity_key]
        if entry.source and entry.source in self._policy.source_overrides:
            return self._policy.source_overrides[entry.source]
        return self._policy.default_retention_days
