"""User impersonation service for admin panels.

Allows super-admin users to temporarily assume the identity of another user
for debugging and support purposes.  Every impersonation session is audit-
logged.  The original admin identity is preserved so it can be restored.

Usage::

    service = ImpersonationService(
        audit_logger=audit_logger,
        policy=my_policy,
    )

    result = await service.start(
        actor=admin_user,
        target_user_id="user-123",
        request=request,
        reason="Support ticket #456",
    )

    if result.is_ok():
        impersonation = result.unwrap()
        # Swap session identity to impersonation.target_user_id ...

    # Later, to restore the original admin identity:
    await service.stop(admin_user, request)

.. note::
    **Intentionally unwired (2026-08-18).** No HTTP route constructs or
    routes to this service — ``UserImpersonationView`` renders an
    "Impersonate" button whose ``hx-post`` target (``/admin/impersonate/
    {user_id}``) is not registered by any controller. Do not wire the
    feature without first closing the three latent design gaps documented
    in ``docs/superpowers/specs/2026-08-16-security-impersonation-design.md``
    §2.1(a)-(c) and §3.1: (a) nested-session overwrite (``start()``
    unconditionally replaces an actor's existing session); (b) no
    target-role restriction (only the actor-side ``can_impersonate`` check
    exists); (c) in-process-dict session storage that is invisible to
    other workers (``get_active_session``/``is_impersonating`` consult
    only ``self._sessions``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid

from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.exceptions import NotFoundError, PermissionDeniedError
from lexigram.admin.rbac.super_admin import is_super_admin
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity, AuditLoggerProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)

# Session-state key used to store impersonation context
_SESSION_KEY = "_admin_impersonation"
# Attribute on request.state that holds original admin identity
_ORIGINAL_USER_KEY = "_impersonation_original_user_id"


@dataclass(frozen=True)
class ImpersonationSession:
    """Represents an active impersonation session.

    Attributes:
        id: Unique impersonation session identifier.
        actor_id: Admin user who initiated the impersonation.
        target_user_id: User being impersonated.
        started_at: UTC timestamp when impersonation began.
        reason: Optional free-text reason for audit trail.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    actor_id: str = ""
    target_user_id: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reason: str = ""


class ImpersonationPolicy:
    """Policy: only holders of the configured super-admin role may impersonate.

    Override ``can_impersonate`` to customise authorisation logic.
    """

    def __init__(self, super_admin_role: str = "superadmin") -> None:
        """Store the role name that grants impersonation rights.

        Args:
            super_admin_role: Role name (default ``"superadmin"``) that
                grants super-admin rights.
        """
        self._super_admin_role = super_admin_role

    def can_impersonate(self, actor: Any) -> bool:
        """Return True if *actor* is allowed to impersonate another user.

        Args:
            actor: The admin user attempting to impersonate.

        Returns:
            True if the actor holds the configured super-admin role.
        """
        return is_super_admin(actor, self._super_admin_role)


@inject
class ImpersonationService:
    """Service that manages user impersonation sessions.

    Args:
        audit_logger: Optional audit logger (AuditLoggerProtocol).
            If ``None``, impersonation events are only logged via the standard
            logger; no structured audit record is persisted.
        policy: Policy object that determines who may impersonate.
            Defaults to ``ImpersonationPolicy`` (superadmin-only).
        active_sessions: Optional pre-populated in-memory store used in tests.
    """

    def __init__(
        self,
        audit_logger: AuditLoggerProtocol | None = None,
        policy: ImpersonationPolicy | None = None,
        active_sessions: dict[str, ImpersonationSession] | None = None,
        rbac_config: AdminRbacConfig | None = None,
    ) -> None:
        self._audit = audit_logger
        self._policy = policy or ImpersonationPolicy(
            super_admin_role=(rbac_config or AdminRbacConfig()).super_admin_role
        )
        # actor_id → active ImpersonationSession
        self._sessions: dict[str, ImpersonationSession] = (
            active_sessions if active_sessions is not None else {}
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(
        self,
        actor: Any,
        target_user_id: str,
        reason: str = "",
        request: Any | None = None,
    ) -> Result[ImpersonationSession, PermissionDeniedError]:
        """Begin impersonating *target_user_id* on behalf of *actor*.

        Args:
            actor: The authenticated admin user requesting impersonation.
            target_user_id: ID of the user to impersonate.
            reason: Free-text reason recorded in the audit trail.
            request: Optional Starlette request — if provided, the
                impersonation token is stored in ``request.session``.

        Returns:
            ``Ok(ImpersonationSession)`` on success, or
            ``Err(PermissionDeniedError)`` if the actor is not authorised.
        """
        actor_id: str = getattr(actor, "id", str(actor))

        if not self._policy.can_impersonate(actor):
            logger.warning(
                "impersonation.denied",
                actor_id=actor_id,
                target_user_id=target_user_id,
            )
            return Err(
                PermissionDeniedError(
                    f"User {actor_id!r} is not authorised to impersonate other users"
                )
            )

        session = ImpersonationSession(
            actor_id=actor_id,
            target_user_id=target_user_id,
            reason=reason,
        )
        self._sessions[actor_id] = session

        if request is not None:
            req_session = getattr(request, "session", None)
            if req_session is not None:
                req_session[_SESSION_KEY] = {
                    "id": session.id,
                    "actor_id": actor_id,
                    "target_user_id": target_user_id,
                    "started_at": session.started_at.isoformat(),
                    "reason": reason,
                }
                req_session[_ORIGINAL_USER_KEY] = actor_id

        await self._emit_audit(
            action="impersonation.start",
            actor_id=actor_id,
            target_user_id=target_user_id,
            session_id=session.id,
            reason=reason,
            request=request,
        )
        logger.info(
            "impersonation.started",
            actor_id=actor_id,
            target_user_id=target_user_id,
            session_id=session.id,
        )
        return Ok(session)

    async def stop(
        self,
        actor: Any,
        request: Any | None = None,
    ) -> Result[str, NotFoundError]:
        """End the active impersonation session for *actor*.

        Args:
            actor: The authenticated admin user (original identity).
            request: Optional Starlette request — session cookie is cleared
                when provided.

        Returns:
            ``Ok(original_user_id)`` or ``Err(NotFoundError)`` when no
            active session exists.
        """
        actor_id: str = getattr(actor, "id", str(actor))

        session = self._sessions.pop(actor_id, None)
        if session is None and request is not None:
            req_session = getattr(request, "session", None)
            if req_session:
                raw = req_session.get(_SESSION_KEY)
                if isinstance(raw, dict):
                    actor_id = raw.get("actor_id", actor_id)
                    session = ImpersonationSession(
                        id=raw.get("id", ""),
                        actor_id=actor_id,
                        target_user_id=raw.get("target_user_id", ""),
                        reason=raw.get("reason", ""),
                    )

        if session is None:
            return Err(NotFoundError("No active impersonation session"))

        if request is not None:
            req_session = getattr(request, "session", None)
            if req_session is not None:
                req_session.pop(_SESSION_KEY, None)
                req_session.pop(_ORIGINAL_USER_KEY, None)

        await self._emit_audit(
            action="impersonation.stop",
            actor_id=session.actor_id,
            target_user_id=session.target_user_id,
            session_id=session.id,
            reason="",
            request=request,
        )
        logger.info(
            "impersonation.stopped",
            actor_id=session.actor_id,
            target_user_id=session.target_user_id,
            session_id=session.id,
        )
        return Ok(session.actor_id)

    def get_active_session(self, actor_id: str) -> ImpersonationSession | None:
        """Return the active ``ImpersonationSession`` for *actor_id*, or ``None``.

        Args:
            actor_id: Admin user ID to look up.

        Returns:
            Active session, or ``None`` if the user is not impersonating.
        """
        return self._sessions.get(actor_id)

    def is_impersonating(self, actor_id: str) -> bool:
        """Return ``True`` if *actor_id* currently has an active impersonation.

        Args:
            actor_id: Admin user ID to check.

        Returns:
            True if an active session exists for this actor.
        """
        return actor_id in self._sessions

    def list_active(self) -> list[ImpersonationSession]:
        """Return all currently active impersonation sessions.

        Returns:
            List of active ``ImpersonationSession`` objects.
        """
        return list(self._sessions.values())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _emit_audit(
        self,
        action: str,
        actor_id: str,
        target_user_id: str,
        session_id: str,
        reason: str,
        request: Any | None,
    ) -> None:
        """Emit an audit log entry if an audit logger is configured."""
        if self._audit is None:
            return

        ip = None
        user_agent = None
        if request is not None:
            client = getattr(request, "client", None)
            ip = getattr(client, "host", None) if client else None
            headers = getattr(request, "headers", {})
            user_agent = headers.get("user-agent")

        await self._audit.log(
            AuditEntry(
                action=action,
                actor_id=actor_id,
                resource_type="admin_user",
                resource_id=target_user_id,
                outcome="success",
                severity=AuditEventSeverity.CRITICAL,
                source="admin",
                metadata={
                    "impersonation_session_id": str(session_id),
                    "reason": str(reason) if reason else "",
                    "ip_address": str(ip) if ip else "",
                    "user_agent": str(user_agent) if user_agent else "",
                },
            )
        )
