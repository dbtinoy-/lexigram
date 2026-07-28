"""Checkpoint manager — creates and restores session snapshots."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from lexigram.ai.session.exceptions import CheckpointNotFoundError
from lexigram.contracts.ai.session import (
    SessionCheckpoint,
    SessionState,
    SessionStoreProtocol,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class CheckpointManager:
    """Creates, loads, and prunes session checkpoints.

    Wraps the store's checkpoint methods with pruning logic so the
    per-session checkpoint count never exceeds the configured maximum.

    Args:
        store: Session store providing checkpoint persistence.
        max_checkpoints_per_session: Maximum checkpoints to retain per session.
    """

    def __init__(
        self, store: SessionStoreProtocol, max_checkpoints_per_session: int = 50
    ) -> None:
        self._store = store
        self._max = max_checkpoints_per_session

    async def create(
        self,
        state: SessionState,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> SessionCheckpoint:
        """Snapshot the current session state as an immutable checkpoint.

        Prunes the oldest checkpoints if the per-session limit is exceeded.

        Args:
            state: The session state to snapshot.
            metadata: Optional metadata to attach to the checkpoint.

        Returns:
            The newly created ``SessionCheckpoint``.
        """
        import copy

        checkpoint = SessionCheckpoint(
            checkpoint_id=str(uuid4()),
            session_id=state.session_id,
            state=copy.deepcopy(state),
            created_at=datetime.now(UTC),
            parent_checkpoint_id=state.checkpoint_id,
            metadata=metadata or {},
        )
        await self._store.save_checkpoint(checkpoint)
        await self._prune(state.session_id)
        logger.info(
            "checkpoint_created",
            session_id=state.session_id,
            checkpoint_id=checkpoint.checkpoint_id,
        )
        return checkpoint

    async def restore(self, checkpoint_id: str) -> SessionState:
        """Restore a session state from a checkpoint.

        Args:
            checkpoint_id: The checkpoint ID to restore.

        Returns:
            Deep copy of the session state at checkpoint time.

        Raises:
            CheckpointNotFoundError: If no checkpoint with that ID exists.
        """
        import copy

        checkpoint = await self._store.load_checkpoint(checkpoint_id)
        if checkpoint is None:
            raise CheckpointNotFoundError(checkpoint_id)
        restored = copy.deepcopy(checkpoint.state)
        restored = replace(
            restored,
            updated_at=datetime.now(UTC),
            checkpoint_id=checkpoint_id,
        )
        logger.info(
            "checkpoint_restored",
            session_id=restored.session_id,
            checkpoint_id=checkpoint_id,
        )
        return restored

    async def list(self, session_id: str) -> list[SessionCheckpoint]:
        """Return all checkpoints for *session_id*, oldest first.

        Args:
            session_id: The session to query.

        Returns:
            List of checkpoints in chronological order.
        """
        return await self._store.list_checkpoints(session_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _prune(self, session_id: str) -> None:
        """Remove oldest checkpoints when the per-session limit is exceeded.

        Args:
            session_id: The session whose checkpoints to prune.
        """
        checkpoints = await self._store.list_checkpoints(session_id)
        if len(checkpoints) <= self._max:
            return
        # Sort oldest-first (by created_at) and delete the excess
        sorted_cp = sorted(checkpoints, key=lambda c: c.created_at)
        excess = sorted_cp[: len(checkpoints) - self._max]
        for cp in excess:
            # Best-effort delete; stores may not expose delete_checkpoint
            if hasattr(self._store, "delete_checkpoint"):
                await self._store.delete_checkpoint(cp.checkpoint_id)


__all__ = ["CheckpointManager"]
