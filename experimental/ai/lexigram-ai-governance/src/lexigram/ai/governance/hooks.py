"""Root hook payload surface for lexigram-ai-governance."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GovernanceAuditRecordedHook",
    "GovernancePersistenceWrittenHook",
    "GovernancePolicyEvaluatedHook",
]


@dataclass(frozen=True, kw_only=True)
class GovernanceAuditRecordedHook:
    """Payload fired when governance audit logging records an event."""

    event_type: str


@dataclass(frozen=True, kw_only=True)
class GovernancePolicyEvaluatedHook:
    """Payload fired when the governance policy layer evaluates a policy."""

    policy_name: str


@dataclass(frozen=True, kw_only=True)
class GovernancePersistenceWrittenHook:
    """Payload fired when governance persistence writes a record."""

    backend: str
