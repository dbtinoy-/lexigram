"""Admin security audit log service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminAuditLogStoreProtocol,
)
from lexigram.admin.auth.types import AdminSecurityEvent, AdminSecurityEventType
from lexigram.contracts.audit import (
    AuditEntry,
    AuditEventSeverity,
    AuditLoggerProtocol,
    AuditQuery,
)
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class AdminAuditLogService:
    """Security event audit log service.

    All methods are fire-tolerant — exceptions are logged but never re-raised.
    Audit failure must never block the authentication flow; a failed audit
    write is strictly less important than completing the operation that
    triggered it (e.g. a login or logout).
    """

    def __init__(
        self,
        store: AdminAuditLogStoreProtocol,
        audit_logger: AuditLoggerProtocol | None = None,
    ) -> None:
        """Initialize with audit log store.

        Args:
            store: Persistence layer for security events.
            audit_logger: Optional unified AuditLoggerProtocol bridge. When
                provided, every event is also forwarded to the centralised
                audit log alongside the admin-specific store.
        """
        self._store = store
        self._audit_logger = audit_logger

    async def log_event(
        self,
        event_type: AdminSecurityEventType,
        ip_address: str,
        user_agent: str,
        success: bool,
        admin_user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a security event. Never raises.

        Swallows all exceptions so that an audit store failure (e.g. database
        unreachable, serialisation error) cannot interrupt the calling auth
        flow.  The failure is recorded at WARNING level so operators are
        notified without surfacing an error to the end user.

        Args:
            event_type: Type of security event.
            ip_address: Client IP.
            user_agent: Client user agent.
            success: Whether the operation succeeded.
            admin_user_id: Associated admin user (None for pre-auth events).
            metadata: Optional structured context dict.
        """
        try:
            # Only primitive-safe values are stored; anything else is coerced
            # to str so that the JSONB/TEXT column always receives serialisable
            # data regardless of what the caller provides.
            safe_meta: dict[str, str | int | bool | None] = {}
            for k, v in (metadata or {}).items():
                if isinstance(v, (str, int, bool)) or v is None:
                    safe_meta[str(k)] = v
                else:
                    safe_meta[str(k)] = str(v)

            event = AdminSecurityEvent(
                id=str(uuid.uuid4()),
                event_type=event_type,
                admin_user_id=admin_user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                metadata=safe_meta,
                created_at=datetime.now(UTC),
            )
            await self._store.insert(event)
            # Bridge to unified audit logger when configured.
            if self._audit_logger is not None:
                try:
                    unified_entry = AuditEntry(
                        action=event_type.value,
                        actor_id=admin_user_id or "",
                        resource_type="admin.security",
                        resource_id=event.id,
                        outcome="success" if success else "failure",
                        source="admin",
                        metadata=dict(safe_meta),
                    )
                    await self._audit_logger.log(unified_entry)
                except Exception:  # noqa: BLE001
                    logger.warning(
                        "audit.bridge_log_failed", event_type=event_type.value
                    )
            logger.debug(
                "audit.event_logged",
                event_type=event_type.value,
                success=success,
                admin_user_id=admin_user_id,
            )
        except Exception:  # noqa: BLE001 — audit failures must never propagate; the store may be unavailable for any reason (DB down, serialisation issue, schema not yet created) and we must not interrupt the auth flow that triggered this log call.
            logger.warning(
                "audit.log_failed",
                event_type=(
                    event_type.value
                    if hasattr(event_type, "value")
                    else str(event_type)
                ),
            )

    async def record(
        self,
        action: str,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        outcome: str,
        severity: AuditEventSeverity = AuditEventSeverity.MEDIUM,
        **metadata: Any,
    ) -> None:
        """Record a single audit event using the framework-wide contract.

        Maps the framework-wide ``AuditLogProtocol.record()`` interface to the
        admin-specific ``log_event()`` method.  Never raises — audit failures
        are swallowed so that an audit store outage cannot interrupt flows.

        Args:
            action: Dot-notation action identifier (e.g. ``auth.login``).
            actor_id: ID of the user or service performing the action.
            resource_type: Type of resource affected.
            resource_id: ID of the resource affected.
            outcome: ``"success"`` or ``"failure"``.
            severity: Severity level (defaults to MEDIUM).
            **metadata: Additional key-value context forwarded to ``log_event``.
        """
        try:
            event_type = AdminSecurityEventType(action)
        except ValueError:
            event_type = AdminSecurityEventType.SUSPICIOUS_ACTIVITY

        meta: dict[str, Any] = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "severity": severity,
            **metadata,
        }
        await self.log_event(
            event_type=event_type,
            ip_address=str(metadata.get("ip_address", "")),
            user_agent=str(metadata.get("user_agent", "")),
            success=outcome == "success",
            admin_user_id=actor_id,
            metadata=meta,
        )

    async def log(self, entry: AuditEntry) -> None:
        """Implement AuditLoggerProtocol.log — forward entry to the admin store.

        Converts the unified AuditEntry to a security event and persists it.
        Never raises.

        Args:
            entry: The canonical audit entry to record.
        """
        try:
            event_type_str = entry.action
            try:
                event_type = AdminSecurityEventType(event_type_str)
            except ValueError:
                event_type = AdminSecurityEventType.SUSPICIOUS_ACTIVITY

            meta: dict[str, Any] = {
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "severity": entry.severity,
                **(entry.metadata or {}),
            }
            await self.log_event(
                event_type=event_type,
                ip_address=str(meta.get("ip_address", "")),
                user_agent=str(meta.get("user_agent", "")),
                success=entry.outcome == "success",
                admin_user_id=entry.actor_id or None,
                metadata=meta,
            )
        except Exception:  # noqa: BLE001
            logger.warning("audit.log_failed", action=entry.action)

    async def query(self, query: AuditQuery) -> list[AuditEntry]:
        """Implement AuditLoggerProtocol.query — returns empty list (admin store uses get_recent_events).

        Admin security events are stored in a separate schema from generic audit
        entries. This method returns an empty list; use ``get_recent_events``
        for admin-specific queries.

        Args:
            query: Filter criteria (not applied to the admin-specific store).

        Returns:
            Always an empty list for this implementation.
        """
        return []

    async def get_recent_events(
        self,
        admin_user_id: str | None = None,
        since_seconds: int = 3600,
        limit: int = 50,
    ) -> list[AdminSecurityEvent]:
        """Retrieve recent security events. Returns empty list on error.

        Swallows all exceptions for consistency with ``log_event`` — the
        audit log is a best-effort observability layer and a read failure
        (e.g. temporary DB outage) must not crash admin dashboards or API
        endpoints that display security history.

        Args:
            admin_user_id: Filter to specific user (None = all users).
            since_seconds: Look-back window in seconds.
            limit: Maximum results to return.

        Returns:
            List of security events, newest first. Empty list on any error.
        """
        try:
            return await self._store.query_recent(
                admin_user_id=admin_user_id,
                since_seconds=since_seconds,
                limit=limit,
            )
        except Exception:  # noqa: BLE001 — a read failure from the audit store (transient DB error, schema missing, etc.) must degrade gracefully; callers receive an empty list rather than a 500 error.
            logger.warning("audit.query_failed", admin_user_id=admin_user_id)
            return []


# Verify structural subtyping at import time: AdminAuditLogService must
# satisfy AdminAuditLogServiceProtocol without explicit inheritance.
_: AdminAuditLogServiceProtocol = AdminAuditLogService.__new__(AdminAuditLogService)

__all__ = ["AdminAuditLogService"]
