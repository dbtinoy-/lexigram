"""Branch manager — fork and merge session timelines."""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from lexigram.ai.session.branching.merge import AppendMerge, MergeStrategy
from lexigram.ai.session.exceptions import (
    CheckpointNotFoundError,
    SessionCapacityError,
    SessionNotFoundError,
)
from lexigram.contracts.ai.session import SessionStoreProtocol
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai.session import SessionState

logger = get_logger(__name__)


class BranchManager:
    """Fork and merge session timelines.

    Enables exploration of alternative conversation paths by creating
    independent branches from a session (or a specific checkpoint).
    Branches can later be merged back into the parent.

    Args:
        store: Session store that persists session states and checkpoints.
        max_branches_per_session: Maximum allowed forks from a single session.
    """

    def __init__(
        self, store: SessionStoreProtocol, max_branches_per_session: int = 10
    ) -> None:
        self._store = store
        self._max_branches = max_branches_per_session

    async def fork(
        self,
        session_id: str,
        branch_name: str,
        *,
        from_checkpoint: str | None = None,
    ) -> SessionState:
        """Fork a session into a new independent branch.

        The branch inherits all turns from the source session (or checkpoint)
        and is assigned a new session ID with ``parent_session_id`` pointing
        back to the origin.

        Args:
            session_id: The session to fork from.
            branch_name: A human-readable name for the branch.
            from_checkpoint: If provided, fork from this checkpoint instead
                of the current live state.

        Returns:
            Newly created branch ``SessionState``.

        Raises:
            SessionNotFoundError: If the session cannot be found.
            CheckpointNotFoundError: If *from_checkpoint* cannot be found.
            SessionCapacityError: If the branch limit is exceeded.
        """
        existing_branches = await self._store.list_sessions(session_id)
        branch_count = sum(
            1 for s in existing_branches if s.parent_session_id == session_id
        )
        if branch_count >= self._max_branches:
            raise SessionCapacityError(
                f"session {session_id!r} already has {branch_count} branches "
                f"(max {self._max_branches})"
            )

        if from_checkpoint:
            checkpoint = await self._store.load_checkpoint(from_checkpoint)
            if checkpoint is None:
                raise CheckpointNotFoundError(from_checkpoint)
            source_state: SessionState | None = checkpoint.state
        else:
            source_state = await self._store.load(session_id)
            if source_state is None:
                raise SessionNotFoundError(session_id)

        assert source_state is not None  # noqa: S101  # raised above when load() returns None
        branched = copy.deepcopy(source_state)
        branched = replace(
            branched,
            session_id=str(uuid4()),
            parent_session_id=session_id,
            branch_name=branch_name,
            checkpoint_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        await self._store.save(branched)
        logger.info(
            "session_forked",
            parent_session_id=session_id,
            branch_session_id=branched.session_id,
            branch_name=branch_name,
        )
        return branched

    async def merge(
        self,
        parent_session_id: str,
        branch_session_id: str,
        *,
        strategy: MergeStrategy | None = None,
    ) -> SessionState:
        """Merge a branch back into its parent session.

        Args:
            parent_session_id: The parent session to merge into.
            branch_session_id: The branch session to merge from.
            strategy: Merge strategy to use; defaults to ``AppendMerge``.

        Returns:
            Updated parent ``SessionState`` with branch content merged in.

        Raises:
            SessionNotFoundError: If either session cannot be found.
        """
        parent = await self._store.load(parent_session_id)
        if parent is None:
            raise SessionNotFoundError(parent_session_id)

        branch = await self._store.load(branch_session_id)
        if branch is None:
            raise SessionNotFoundError(branch_session_id)

        effective_strategy: MergeStrategy = strategy or AppendMerge()
        merged = await effective_strategy.merge(parent, branch)
        merged = replace(merged, updated_at=datetime.now(UTC))
        await self._store.save(merged)
        logger.info(
            "session_merged",
            parent_session_id=parent_session_id,
            branch_session_id=branch_session_id,
        )
        return merged


__all__ = ["BranchManager"]
