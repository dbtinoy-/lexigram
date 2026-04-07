"""Admin Session Manager — pure session-lifecycle business logic.

All persistence is delegated to an injected ``SessionRepositoryProtocol``. This
module contains no SQL, no DDL, and no driver-specific code.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
import uuid

from lexigram.contracts.auth.fingerprint import generate_device_id
from lexigram.contracts.auth.models import UserSession
from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class AdminSessionManager:
    """Lifecycle manager for admin user sessions.

    Enforces concurrency limits, expiry, and activity tracking.  All I/O is
    performed through the injected ``SessionRepositoryProtocol`` so the class remains
    fully testable without a real database.
    """

    DEFAULT_EXPIRY_DAYS = 30
    MAX_CONCURRENT_SESSIONS = 5

    def __init__(self, repo: SessionRepositoryProtocol) -> None:
        """Initialise with the session repository.

        Args:
            repo: Persistence abstraction for session records.  Injected by
                the DI container; typically backed by
                ``AdminSessionSqlRepository``.
        """
        self._repo = repo

    async def create_session(
        self,
        user_id: str,
        fingerprint_data: dict[str, Any],
        ip_address: str | None = None,
        user_agent: str | None = None,
        expires_days: int = DEFAULT_EXPIRY_DAYS,
    ) -> UserSession:
        """Create and persist a new admin session.

        Enforces ``MAX_CONCURRENT_SESSIONS`` by revoking the oldest session
        when the limit is reached before creating a new one.

        Args:
            user_id: Admin user identifier.
            fingerprint_data: Device/browser fingerprint dict used to derive
                a stable ``device_id``.
            ip_address: Originating IP (optional, for audit metadata).
            user_agent: Request User-Agent header (optional).
            expires_days: Session lifetime in days.

        Returns:
            Hydrated ``UserSession`` for the newly created session.
        """
        device_id = generate_device_id(fingerprint_data)
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=expires_days)

        # Enforce concurrent-session cap — evict oldest first.
        active = await self.get_active_sessions(user_id)
        if len(active) >= self.MAX_CONCURRENT_SESSIONS:
            oldest = min(active, key=lambda s: s.last_active_at or s.created_at)  # type: ignore[arg-type, return-value]
            await self.revoke_session(oldest.session_id)
            logger.info("Evicted oldest admin session for user %s", user_id)

        session_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "session_id": session_id,
            "admin_id": user_id,
            "device_id": device_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "fingerprint": fingerprint_data,
            "expires_at": expires_at,
        }

        await self._repo.insert(payload)

        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address or "",
            user_agent=user_agent or "",
            fingerprint=fingerprint_data,
            expires_at=expires_at,
            created_at=now,
            last_active_at=now,
            is_active=True,
        )

        logger.info("Created admin session %s for user %s", session_id, user_id)
        return session

    async def validate_session(self, session_id: str) -> UserSession | None:
        """Validate a session and refresh its activity timestamp.

        Args:
            session_id: Opaque session identifier to validate.

        Returns:
            Hydrated ``UserSession`` if active and unexpired, else ``None``.
        """
        row = await self._repo.find_active(session_id)
        if not row:
            return None

        expires_at = row.get("expires_at")
        if expires_at and datetime.now(UTC) > expires_at:
            await self.revoke_session(session_id)
            logger.warning("Admin session %s expired", session_id)
            return None

        await self.update_activity(session_id)
        return self._row_to_session(row)

    async def get_session(self, session_id: str) -> UserSession | None:
        """Retrieve an admin session by ID without refreshing activity.

        Args:
            session_id: Opaque session identifier.

        Returns:
            Hydrated ``UserSession``, or ``None`` when absent or inactive.
        """
        row = await self._repo.find_active(session_id)
        if not row:
            return None

        expires_at = row.get("expires_at")
        if expires_at and datetime.now(UTC) > expires_at:
            await self.revoke_session(session_id)
            return None

        return self._row_to_session(row)

    async def get_active_sessions(self, user_id: str) -> list[UserSession]:
        """Return all active, non-expired sessions for an admin user.

        Args:
            user_id: Admin owner identifier.

        Returns:
            List of ``UserSession`` objects, newest-activity first.
        """
        rows = await self._repo.find_active_by_user(user_id, datetime.now(UTC))
        return [self._row_to_session(r) for r in rows]

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a single admin session.

        Args:
            session_id: Session to deactivate.

        Returns:
            ``True`` after successful revocation.
        """
        await self._repo.revoke(session_id)
        logger.info("Revoked admin session %s", session_id)
        return True

    async def revoke_all_sessions(self, user_id: str) -> int:
        """Revoke every active session for an admin user.

        Args:
            user_id: Owner whose sessions are to be revoked.

        Returns:
            ``1`` to indicate the operation ran (count of affected sessions
            is not surfaced by all backends).
        """
        await self._repo.revoke_all(user_id)
        logger.info("Revoked all admin sessions for user %s", user_id)
        return 1

    async def update_activity(self, session_id: str) -> bool:
        """Refresh the last-active timestamp for a session.

        Args:
            session_id: Session to touch.

        Returns:
            ``True`` after the update is sent to the repository.
        """
        await self._repo.update_activity(session_id, datetime.now(UTC))
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_session(row: dict[str, Any]) -> UserSession:
        """Map a raw repository row dict to a ``UserSession`` value object."""
        return UserSession(
            session_id=row["session_id"],
            user_id=row["admin_id"],
            device_id=row.get("device_id", ""),
            ip_address=row.get("ip_address", ""),
            user_agent=row.get("user_agent", ""),
            fingerprint=row.get("fingerprint", {}),
            expires_at=row.get("expires_at"),
            created_at=row.get("created_at"),
            last_active_at=row.get("last_active_at"),
            is_active=row.get("is_active", True),
        )
