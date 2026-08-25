"""Audit recording for resource manager operations."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.audit import (
    AuditEntry,
    AuditEventSeverity,
    AuditLoggerProtocol,
)


async def record_audit(
    audit_logger: AuditLoggerProtocol | None,
    resource_name: str,
    *,
    action: str,
    actor: Any,
    resource_id: str,
    outcome: str,
    severity: AuditEventSeverity,
    **metadata: object,
) -> None:
    """Record an audit event for a resource operation.

    No-op when no audit logger is configured.

    Args:
        audit_logger: Optional audit logger; ``None`` skips recording.
        resource_name: Name of the resource being operated on.
        action: Fully-qualified action name (e.g. ``admin.resource.create``).
        actor: Acting user (or any object with an ``id`` attribute).
        resource_id: Identifier of the affected record.
        outcome: Outcome label (e.g. ``success``).
        severity: Severity assigned to the audit entry.
        **metadata: Additional structured metadata for the entry.
    """
    if audit_logger is None:
        return

    actor_id = getattr(actor, "id", str(actor))
    await audit_logger.log(
        AuditEntry(
            action=action,
            actor_id=actor_id,
            resource_type=resource_name,
            resource_id=resource_id,
            outcome=outcome,
            severity=severity,
            metadata=dict(metadata),
            source="admin",
        )
    )


__all__ = ["record_audit"]
