"""Session manager service using Result pattern."""

from __future__ import annotations

from lexigram.contracts.ai.session import SessionError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class SessionManagerWithResultPattern:
    """Session manager using Result pattern."""

    async def create_session(self, user_id: str) -> Result[str, SessionError]:
        """Create a new session."""
        try:
            if not user_id:
                return Err(SessionError("User ID cannot be empty"))
            session_id = f"session:{user_id}"
            logger.info("session_created", user_id=user_id, session_id=session_id)
            return Ok(session_id)
        except (RuntimeError, ValueError) as exc:
            logger.error("session_creation_failed", error=str(exc))
            return Err(SessionError(f"Session creation failed: {exc}"))

    async def get_session(self, session_id: str) -> Result[dict | None, SessionError]:
        """Get session data."""
        try:
            if not session_id:
                return Err(SessionError("Session ID cannot be empty"))
            logger.info("session_retrieved", session_id=session_id)
            return Ok(None)
        except (RuntimeError, ValueError) as exc:
            logger.error("session_retrieval_failed", error=str(exc))
            return Err(SessionError(f"Session retrieval failed: {exc}"))


__all__ = ["SessionManagerWithResultPattern"]
