"""Protocols for admin security audit logging."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from lexigram.contracts.audit import AuditLoggerProtocol

if TYPE_CHECKING:
    from lexigram.admin.auth.types import AdminSecurityEvent, AdminSecurityEventType


@runtime_checkable
class AdminAuditLogStoreProtocol(Protocol):
    """Persistence protocol for security audit log entries."""

    async def ensure_schema(self) -> None:
        """Create the admin_security_audit_log table if it does not exist."""
        ...

    async def insert(self, event: AdminSecurityEvent) -> None:
        """Persist a security event.

        Args:
            event: Security event to store.
        """
        ...

    async def query_recent(
        self,
        admin_user_id: str | None = None,
        event_type: AdminSecurityEventType | None = None,
        since_seconds: int = 3600,
        limit: int = 100,
    ) -> list[AdminSecurityEvent]:
        """Query recent security events with optional filters.

        Args:
            admin_user_id: Filter to specific user (None = all users).
            event_type: Filter to specific event type (None = all types).
            since_seconds: Look-back window in seconds.
            limit: Maximum records to return.

        Returns:
            List of matching security events, newest first.
        """
        ...


@runtime_checkable
class AdminAuditLogServiceProtocol(AuditLoggerProtocol, Protocol):
    """Service for recording admin security events.

    Extends the framework-wide ``AuditLoggerProtocol`` so that admin audit
    implementations satisfy the cross-package contract. Adds admin-specific
    methods (``log_event``, ``get_recent_events``) on top of the base
    ``log()`` and ``query()`` methods from ``AuditLoggerProtocol``.

    Implementations must never raise — audit failures are swallowed so that
    an audit store outage cannot interrupt authentication flows.
    """

    async def log_event(
        self,
        event_type: AdminSecurityEventType,
        ip_address: str,
        user_agent: str,
        success: bool,
        admin_user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a security event. Implementation must never raise.

        Args:
            event_type: Type of security event.
            ip_address: Client IP.
            user_agent: Client user agent.
            success: Whether the operation succeeded.
            admin_user_id: Associated admin user (None for pre-auth events).
            metadata: Optional structured context.
        """
        ...

    async def get_recent_events(
        self,
        admin_user_id: str | None = None,
        since_seconds: int = 3600,
        limit: int = 50,
    ) -> list[AdminSecurityEvent]:
        """Retrieve recent security events for display.

        Args:
            admin_user_id: Filter to specific user.
            since_seconds: Look-back window.
            limit: Maximum results.

        Returns:
            List of security events, newest first.
        """
        ...
