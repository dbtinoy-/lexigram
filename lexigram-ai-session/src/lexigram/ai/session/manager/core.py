"""Session manager — central orchestrator for session lifecycle."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from lexigram.ai.session.exceptions import (
    CheckpointNotFoundError,
    SessionCapacityError,
    SessionClosedError,
    SessionNotFoundError,
)
from lexigram.ai.session.state import SessionStateMachine
from lexigram.contracts.ai.memory import MemoryEntry, WorkingMemoryProtocol
from lexigram.contracts.ai.session import (
    SessionCheckpoint,
    SessionManagerProtocol,
    SessionState,
    SessionStatus,
    SessionStoreProtocol,
    SessionTurn,
)
from lexigram.ai.session.config import SessionConfig
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class SessionManagerImpl(SessionManagerProtocol):
    """Manages session lifecycle with persistence and optional memory integration.

    Implements ``SessionManagerProtocol``. Orchestrates create, resume,
    suspend, close, add_turn, checkpoint, and restore operations. Publishes
    domain events via an optional event bus and triggers memory consolidation
    on session close when a consolidator is available.

    Constructor parameters are injected by the DI container; every dependency
    except *config* and *store* is optional to allow graceful degradation.

    Args:
        config: Session configuration.
        store: Persistence backend for session state and checkpoints.
        memory: Optional working memory for recording turns.
        consolidator: Optional memory consolidator triggered on close.
        event_bus: Optional event bus for lifecycle events.
    """

    def __init__(
        self,
        config: SessionConfig,
        store: SessionStoreProtocol,
        memory: WorkingMemoryProtocol | None = None,
        consolidator: Any | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self._config = config
        self._store = store
        self._memory = memory
        self._consolidator = consolidator
        self._event_bus = event_bus
        self._fsm = SessionStateMachine()
        self._background_tasks: set[asyncio.Task[Any]] = set()

    # ------------------------------------------------------------------
    # SessionManagerProtocol
    # ------------------------------------------------------------------

    async def create(
        self,
        user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> SessionState:
        """Create a new session.

        Args:
            user_id: The owning user.
            metadata: Optional session metadata.

        Returns:
            Newly created ``SessionState`` with status ``active``.

        Raises:
            SessionCapacityError: If the per-user session limit is reached.
        """
        existing = await self._store.list_sessions(user_id)
        active_count = sum(1 for s in existing if s.status != SessionStatus.CLOSED)
        if active_count >= self._config.max_sessions_per_user:
            raise SessionCapacityError(
                f"user {user_id!r} already has {active_count} active sessions "
                f"(max {self._config.max_sessions_per_user})"
            )

        now = datetime.now(UTC)
        state = SessionState(
            session_id=str(uuid4()),
            user_id=user_id,
            status=SessionStatus.ACTIVE,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )
        await self._store.save(state)
        await self._emit("session.created", state)
        logger.info("session_created", session_id=state.session_id, user_id=user_id)
        return state

    async def resume(self, session_id: str) -> SessionState | None:
        """Resume an existing session.

        Transitions SUSPENDED → ACTIVE.  Returns the updated state or ``None``
        if the session does not exist.

        Args:
            session_id: ID of the session to resume.

        Returns:
            Updated ``SessionState``, or ``None`` if not found.

        Raises:
            SessionClosedError: If the session is already closed.
        """
        state = await self._store.load(session_id)
        if state is None:
            return None
        if state.status == SessionStatus.CLOSED:
            raise SessionClosedError(session_id)
        self._fsm.validate(session_id, state.status.value, SessionStatus.ACTIVE.value)
        state = replace(
            state,
            status=SessionStatus.ACTIVE,
            updated_at=datetime.now(UTC),
        )
        await self._store.save(state)
        await self._emit("session.resumed", state)
        logger.info("session_resumed", session_id=session_id)
        return state

    async def add_turn(self, session_id: str, turn: SessionTurn) -> None:
        """Add a conversation turn and update session metrics.

        Also records the turn in working memory if available, and triggers
        an auto-checkpoint when the configured interval is reached.

        Args:
            session_id: Target session ID.
            turn: The turn to append.

        Raises:
            SessionNotFoundError: If the session does not exist.
            SessionClosedError: If the session is closed.
            SessionCapacityError: If the per-session turn limit is reached.
        """
        state = await self._store.load(session_id)
        if state is None:
            raise SessionNotFoundError(session_id)
        if state.status == SessionStatus.CLOSED:
            raise SessionClosedError(session_id)
        if len(state.turns) >= self._config.max_turns_per_session:
            raise SessionCapacityError(
                f"session {session_id!r} has reached the turn limit "
                f"({self._config.max_turns_per_session})"
            )

        state.turns.append(turn)
        state = replace(
            state,
            turn_count=state.turn_count + 1,
            total_tokens=state.total_tokens + turn.tokens_used,
            total_cost=state.total_cost + turn.cost,
            updated_at=datetime.now(UTC),
        )

        if self._memory is not None:
            entry = MemoryEntry(
                id=turn.turn_id,
                content=turn.content,
                role=turn.role,
                timestamp=turn.timestamp,
                metadata=turn.metadata,
            )
            await self._memory.add(entry)

        await self._store.save(state)

        if (
            self._config.auto_checkpoint_interval
            and state.turn_count % self._config.auto_checkpoint_interval == 0
        ):
            await self.checkpoint(session_id)

    async def get_state(self, session_id: str) -> SessionState | None:
        """Return the current state of a session, or ``None`` if not found.

        Args:
            session_id: The session ID to look up.

        Returns:
            ``SessionState`` or ``None``.
        """
        return await self._store.load(session_id)

    async def checkpoint(self, session_id: str) -> SessionCheckpoint:
        """Create an immutable snapshot of the current session state.

        Args:
            session_id: The session to snapshot.

        Returns:
            The created ``SessionCheckpoint``.

        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        state = await self._store.load(session_id)
        if state is None:
            raise SessionNotFoundError(session_id)

        import copy

        checkpoint = SessionCheckpoint(
            checkpoint_id=str(uuid4()),
            session_id=session_id,
            state=copy.deepcopy(state),
            created_at=datetime.now(UTC),
            parent_checkpoint_id=state.checkpoint_id,
        )
        state = replace(state, checkpoint_id=checkpoint.checkpoint_id)
        await self._store.save(state)
        await self._store.save_checkpoint(checkpoint)
        logger.info(
            "session_checkpointed",
            session_id=session_id,
            checkpoint_id=checkpoint.checkpoint_id,
        )
        return checkpoint

    async def restore(self, checkpoint_id: str) -> SessionState:
        """Restore a session to a previous checkpoint.

        Args:
            checkpoint_id: The checkpoint to restore from.

        Returns:
            The restored ``SessionState``.

        Raises:
            CheckpointNotFoundError: If the checkpoint does not exist.
        """
        checkpoint = await self._store.load_checkpoint(checkpoint_id)
        if checkpoint is None:
            raise CheckpointNotFoundError(checkpoint_id)

        import copy

        restored = copy.deepcopy(checkpoint.state)
        restored = replace(
            restored,
            updated_at=datetime.now(UTC),
            checkpoint_id=checkpoint_id,
        )
        await self._store.save(restored)
        await self._emit("session.restored", restored)
        logger.info(
            "session_restored",
            session_id=restored.session_id,
            checkpoint_id=checkpoint_id,
        )
        return restored

    async def close(self, session_id: str) -> None:
        """Close a session and optionally trigger memory consolidation.

        Args:
            session_id: The session to close.

        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        state = await self._store.load(session_id)
        if state is None:
            raise SessionNotFoundError(session_id)

        self._fsm.validate(session_id, state.status.value, SessionStatus.CLOSED.value)
        state = replace(
            state,
            status=SessionStatus.CLOSED,
            updated_at=datetime.now(UTC),
        )
        await self._store.save(state)

        if self._consolidator is not None and self._config.consolidate_on_close:
            task = asyncio.create_task(
                self._consolidator.consolidate(session_id=session_id)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        await self._emit("session.closed", state)
        logger.info("session_closed", session_id=session_id)

    async def suspend(self, session_id: str) -> SessionState:
        """Suspend an active session without closing it.

        Args:
            session_id: The session to suspend.

        Returns:
            Updated ``SessionState`` with status ``suspended``.

        Raises:
            SessionNotFoundError: If the session does not exist.
            SessionTransitionError: If the session cannot be suspended.
        """
        state = await self._store.load(session_id)
        if state is None:
            raise SessionNotFoundError(session_id)
        self._fsm.validate(
            session_id, state.status.value, SessionStatus.SUSPENDED.value
        )
        state = replace(
            state,
            status=SessionStatus.SUSPENDED,
            updated_at=datetime.now(UTC),
        )
        await self._store.save(state)
        await self._emit("session.suspended", state)
        logger.info("session_suspended", session_id=session_id)
        return state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _emit(self, event_type: str, state: SessionState) -> None:
        """Publish a session lifecycle event if an event bus is configured.

        Args:
            event_type: Dot-separated event name (e.g. ``session.created``).
            state: The session state associated with the event.
        """
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                event_type,
                {"session_id": state.session_id, "status": state.status.value},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "session_event_publish_failed", event_type=event_type, error=str(exc)
            )

    async def dispose(self) -> None:
        """Container dispose hook. No-op — shutdown is handled by SessionProvider."""


__all__ = ["SessionManagerImpl"]
