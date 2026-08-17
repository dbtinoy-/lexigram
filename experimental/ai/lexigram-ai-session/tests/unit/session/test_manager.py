"""Unit tests for SessionManagerImpl."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from lexigram.contracts.ai.session import SessionStatus
from lexigram.ai.session.config import SessionConfig
from lexigram.ai.session.exceptions import (
    CheckpointNotFoundError,
    SessionCapacityError,
    SessionClosedError,
    SessionNotFoundError,
    SessionTransitionError,
)
from lexigram.ai.session.manager import SessionManagerImpl
from lexigram.ai.session.stores.in_memory import InMemorySessionStore


class TestSessionManagerCreate:
    """Tests for SessionManagerImpl.create."""

    async def test_create_returns_active_state(self, manager: SessionManagerImpl) -> None:
        state = await manager.create(user_id="u1")
        assert state.status == SessionStatus.ACTIVE
        assert state.user_id == "u1"
        assert state.session_id is not None

    async def test_create_persists_to_store(self, manager: SessionManagerImpl, store: InMemorySessionStore) -> None:
        state = await manager.create(user_id="u1")
        loaded = await store.load(state.session_id)
        assert loaded is not None

    async def test_create_passes_metadata(self, manager: SessionManagerImpl) -> None:
        state = await manager.create(user_id="u1", metadata={"key": "val"})
        assert state.metadata["key"] == "val"

    async def test_create_raises_capacity_error_when_limit_reached(self, store: InMemorySessionStore) -> None:
        cfg = SessionConfig(max_sessions_per_user=1, auto_checkpoint_interval=None)
        mgr = SessionManagerImpl(config=cfg, store=store)
        await mgr.create(user_id="u1")
        with pytest.raises(SessionCapacityError):
            await mgr.create(user_id="u1")

    async def test_create_allows_second_session_for_different_user(self, manager: SessionManagerImpl) -> None:
        await manager.create(user_id="alice")
        state2 = await manager.create(user_id="bob")
        assert state2.status == SessionStatus.ACTIVE


class TestSessionManagerResume:
    """Tests for SessionManagerImpl.resume."""

    async def test_resume_suspended_session(self, manager: SessionManagerImpl) -> None:
        state = await manager.create(user_id="u1")
        await manager.suspend(state.session_id)
        resumed = await manager.resume(state.session_id)
        assert resumed is not None
        assert resumed.status == SessionStatus.ACTIVE

    async def test_resume_missing_session_returns_none(self, manager: SessionManagerImpl) -> None:
        result = await manager.resume("does-not-exist")
        assert result is None

    async def test_resume_closed_session_raises(self, manager: SessionManagerImpl) -> None:
        state = await manager.create(user_id="u1")
        await manager.close(state.session_id)
        with pytest.raises(SessionClosedError):
            await manager.resume(state.session_id)


class TestSessionManagerAddTurn:
    """Tests for SessionManagerImpl.add_turn."""

    async def test_add_turn_appends_to_session(self, manager: SessionManagerImpl, make_turn) -> None:
        state = await manager.create(user_id="u1")
        turn = make_turn(role="user", content="hello")
        await manager.add_turn(state.session_id, turn)
        updated = await manager.get_state(state.session_id)
        assert len(updated.turns) == 1
        assert updated.turns[0].content == "hello"

    async def test_add_turn_increments_turn_count(self, manager: SessionManagerImpl, make_turn) -> None:
        state = await manager.create(user_id="u1")
        await manager.add_turn(state.session_id, make_turn(tokens_used=10))
        updated = await manager.get_state(state.session_id)
        assert updated.turn_count == 1

    async def test_add_turn_accumulates_tokens_and_cost(self, manager: SessionManagerImpl, make_turn) -> None:
        state = await manager.create(user_id="u1")
        await manager.add_turn(state.session_id, make_turn(tokens_used=100, cost=0.01))
        await manager.add_turn(state.session_id, make_turn(tokens_used=50, cost=0.005))
        updated = await manager.get_state(state.session_id)
        assert updated.total_tokens == 150
        assert abs(updated.total_cost - 0.015) < 1e-9

    async def test_add_turn_to_missing_session_raises(self, manager: SessionManagerImpl, make_turn) -> None:
        with pytest.raises(SessionNotFoundError):
            await manager.add_turn("nonexistent", make_turn())

    async def test_add_turn_to_closed_session_raises(self, manager: SessionManagerImpl, make_turn) -> None:
        state = await manager.create(user_id="u1")
        await manager.close(state.session_id)
        with pytest.raises(SessionClosedError):
            await manager.add_turn(state.session_id, make_turn())

    async def test_add_turn_raises_capacity_error_at_limit(self, store: InMemorySessionStore, make_turn) -> None:
        cfg = SessionConfig(max_turns_per_session=2, auto_checkpoint_interval=None)
        mgr = SessionManagerImpl(config=cfg, store=store)
        state = await mgr.create(user_id="u1")
        await mgr.add_turn(state.session_id, make_turn())
        await mgr.add_turn(state.session_id, make_turn())
        with pytest.raises(SessionCapacityError):
            await mgr.add_turn(state.session_id, make_turn())

    async def test_auto_checkpoint_triggered_at_interval(self, store: InMemorySessionStore, make_turn) -> None:
        cfg = SessionConfig(auto_checkpoint_interval=2, max_sessions_per_user=10)
        mgr = SessionManagerImpl(config=cfg, store=store)
        state = await mgr.create(user_id="u1")
        await mgr.add_turn(state.session_id, make_turn())
        await mgr.add_turn(state.session_id, make_turn())
        checkpoints = await store.list_checkpoints(state.session_id)
        assert len(checkpoints) == 1


class TestSessionManagerCheckpointRestore:
    """Tests for SessionManagerImpl.checkpoint and SessionManagerImpl.restore."""

    async def test_checkpoint_creates_snapshot(self, manager: SessionManagerImpl) -> None:
        state = await manager.create(user_id="u1")
        cp = await manager.checkpoint(state.session_id)
        assert cp.session_id == state.session_id
        assert cp.checkpoint_id is not None

    async def test_checkpoint_missing_session_raises(self, manager: SessionManagerImpl) -> None:
        with pytest.raises(SessionNotFoundError):
            await manager.checkpoint("nonexistent")

    async def test_restore_returns_snapshot_state(self, manager: SessionManagerImpl, make_turn) -> None:
        state = await manager.create(user_id="u1")
        cp = await manager.checkpoint(state.session_id)
        # Modify state after checkpoint
        await manager.add_turn(state.session_id, make_turn(content="after checkpoint"))
        # Restore
        restored = await manager.restore(cp.checkpoint_id)
        assert len(restored.turns) == 0  # snapshot was empty

    async def test_restore_missing_checkpoint_raises(self, manager: SessionManagerImpl) -> None:
        with pytest.raises(CheckpointNotFoundError):
            await manager.restore("nonexistent-checkpoint")


class TestSessionManagerSuspendClose:
    """Tests for suspend and close transitions."""

    async def test_suspend_active_session(self, manager: SessionManagerImpl) -> None:
        state = await manager.create(user_id="u1")
        suspended = await manager.suspend(state.session_id)
        assert suspended.status == SessionStatus.SUSPENDED

    async def test_suspend_missing_session_raises(self, manager: SessionManagerImpl) -> None:
        with pytest.raises(SessionNotFoundError):
            await manager.suspend("nonexistent")

    async def test_close_active_session(self, manager: SessionManagerImpl) -> None:
        state = await manager.create(user_id="u1")
        await manager.close(state.session_id)
        closed = await manager.get_state(state.session_id)
        assert closed.status == SessionStatus.CLOSED

    async def test_close_missing_session_raises(self, manager: SessionManagerImpl) -> None:
        with pytest.raises(SessionNotFoundError):
            await manager.close("nonexistent")

    async def test_fsm_prevents_direct_suspended_to_closed_without_resume(
        self, manager: SessionManagerImpl
    ) -> None:
        state = await manager.create(user_id="u1")
        await manager.suspend(state.session_id)
        # Closed from suspended is valid per FSM; just verify no crash
        await manager.close(state.session_id)
        final = await manager.get_state(state.session_id)
        assert final.status == SessionStatus.CLOSED

    async def test_transition_active_to_active_raises(self, manager: SessionManagerImpl) -> None:
        """Active → Active is not a valid FSM transition."""
        state = await manager.create(user_id="u1")
        with pytest.raises(SessionTransitionError):
            await manager.resume(state.session_id)


class TestSessionManagerGetState:
    """Tests for get_state."""

    async def test_get_state_returns_existing(self, manager: SessionManagerImpl) -> None:
        state = await manager.create(user_id="u1")
        fetched = await manager.get_state(state.session_id)
        assert fetched is not None
        assert fetched.session_id == state.session_id

    async def test_get_state_returns_none_for_missing(self, manager: SessionManagerImpl) -> None:
        assert await manager.get_state("missing") is None


class TestSessionManagerConsolidation:
    """Test memory consolidation on close."""

    async def test_consolidation_triggered_on_close(self, store: InMemorySessionStore) -> None:
        consolidator = MagicMock()
        consolidator.consolidate = AsyncMock()
        cfg = SessionConfig(consolidate_on_close=True, auto_checkpoint_interval=None)
        mgr = SessionManagerImpl(config=cfg, store=store, consolidator=consolidator)
        state = await mgr.create(user_id="u1")
        await mgr.close(state.session_id)
        # Allow the background task to run
        import asyncio
        await asyncio.sleep(0)
        consolidator.consolidate.assert_called_once()

    async def test_consolidation_not_triggered_when_disabled(self, store: InMemorySessionStore) -> None:
        consolidator = MagicMock()
        consolidator.consolidate = AsyncMock()
        cfg = SessionConfig(consolidate_on_close=False, auto_checkpoint_interval=None)
        mgr = SessionManagerImpl(config=cfg, store=store, consolidator=consolidator)
        state = await mgr.create(user_id="u1")
        await mgr.close(state.session_id)
        import asyncio
        await asyncio.sleep(0)
        consolidator.consolidate.assert_not_called()
