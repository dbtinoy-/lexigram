"""Admin session lifecycle management protocol."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AdminSessionServiceProtocol(Protocol):
    """Admin session lifecycle management service."""

    async def create_session(
        self,
        user_id: str,
        email: str,
        roles: list[str],
        ip_address: str,
        user_agent: str,
    ) -> str:
        """Create a new session and return the session ID.

        Args:
            user_id: Admin user UUID.
            email: Admin user email.
            roles: User's roles.
            ip_address: Client IP.
            user_agent: Client user agent.

        Returns:
            New session identifier (secrets.token_urlsafe(32)).
        """
        ...

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session data if valid (not expired, not revoked).

        Checks both idle timeout and absolute expiry.

        Args:
            session_id: Session to retrieve.

        Returns:
            Session data dict or None if not found/expired.
        """
        ...

    async def touch_session(self, session_id: str) -> None:
        """Update session last-active timestamp.

        Args:
            session_id: Session to touch.
        """
        ...

    async def revoke_session(self, session_id: str) -> None:
        """Revoke a single session.

        Args:
            session_id: Session to revoke.
        """
        ...

    async def revoke_all_user_sessions(self, user_id: str) -> None:
        """Revoke all sessions for a user.

        Args:
            user_id: Admin user UUID.
        """
        ...
