"""Root hook payload surface for lexigram-audit.

Defines canonical payload dataclasses for audit lifecycle hook points.
Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AuditEntryCreatedHook",
    "AuditPurgeScheduledHook",
    "AuditVerificationScheduledHook",
]


@dataclass(frozen=True, kw_only=True)
class AuditEntryCreatedHook:
    """Payload fired when an audit entry is about to be persisted.

    Attributes:
        action: Dot-notation action identifier.
        actor_id: ID of the actor performing the action.
        resource_type: Kind of affected resource.
    """

    action: str
    actor_id: str
    resource_type: str = ""


@dataclass(frozen=True, kw_only=True)
class AuditVerificationScheduledHook:
    """Payload fired when a verification run is triggered.

    Attributes:
        batch_size: Number of entries to verify in this run.
    """

    batch_size: int


@dataclass(frozen=True, kw_only=True)
class AuditPurgeScheduledHook:
    """Payload fired when a retention purge is triggered.

    Attributes:
        policy_name: Name of the retention policy being applied.
    """

    policy_name: str
