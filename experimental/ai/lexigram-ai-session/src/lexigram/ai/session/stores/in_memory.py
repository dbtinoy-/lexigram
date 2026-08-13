"""In-memory session store — for development and testing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.ai.session import (
        SessionCheckpoint,
        SessionState,
    )


class InMemorySessionStore:
    """In-process session and checkpoint storage.

    All data is stored in plain Python dicts and is lost when the process
    exits.  Suitable for development, testing, and single-process deployments.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._checkpoints: dict[str, SessionCheckpoint] = {}

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    async def save(self, state: SessionState) -> None:
        """Persist or overwrite a session state.

        Args:
            state: The session state to save.
        """
        self._sessions[state.session_id] = state

    async def load(self, session_id: str) -> SessionState | None:
        """Return the session state for *session_id*, or ``None``.

        Args:
            session_id: The session to load.

        Returns:
            The session state, or ``None`` if not found.
        """
        return self._sessions.get(session_id)

    async def delete(self, session_id: str) -> None:
        """Remove a session from the store.

        Args:
            session_id: The session to delete.
        """
        self._sessions.pop(session_id, None)

    async def list_sessions(self, user_id: str) -> list[SessionState]:
        """List all sessions belonging to *user_id*.

        Args:
            user_id: The user to filter by.

        Returns:
            All sessions owned by that user.
        """
        return [s for s in self._sessions.values() if s.user_id == user_id]

    # ------------------------------------------------------------------
    # Checkpoint CRUD
    # ------------------------------------------------------------------

    async def save_checkpoint(self, checkpoint: SessionCheckpoint) -> None:
        """Persist an immutable session checkpoint.

        Args:
            checkpoint: The checkpoint to store.
        """
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint

    async def load_checkpoint(self, checkpoint_id: str) -> SessionCheckpoint | None:
        """Return the checkpoint for *checkpoint_id*, or ``None``.

        Args:
            checkpoint_id: The checkpoint to load.

        Returns:
            The checkpoint, or ``None`` if not found.
        """
        return self._checkpoints.get(checkpoint_id)

    async def list_checkpoints(self, session_id: str) -> list[SessionCheckpoint]:
        """List all checkpoints for *session_id*, sorted oldest-first.

        Args:
            session_id: The session to query.

        Returns:
            Checkpoints in chronological order.
        """
        return sorted(
            (c for c in self._checkpoints.values() if c.session_id == session_id),
            key=lambda c: c.created_at,
        )

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Remove a checkpoint from the store.

        Args:
            checkpoint_id: The checkpoint to delete.
        """
        self._checkpoints.pop(checkpoint_id, None)

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    async def expire_old_sessions(self, ttl_seconds: int) -> int:
        """Delete sessions whose last update is older than *ttl_seconds*.

        Args:
            ttl_seconds: Maximum allowed age in seconds.

        Returns:
            Number of sessions expired.
        """
        now = datetime.now(UTC)
        expired_ids = [
            sid
            for sid, state in self._sessions.items()
            if (now - state.updated_at).total_seconds() > ttl_seconds
        ]
        for sid in expired_ids:
            del self._sessions[sid]
        return len(expired_ids)


__all__ = ["InMemorySessionStore"]
