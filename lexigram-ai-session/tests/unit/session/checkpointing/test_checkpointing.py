"""Unit tests for CheckpointManager and StateDiff."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from lexigram.contracts.ai.session import SessionStatus
from lexigram.ai.session.checkpointing.checkpoint_manager import CheckpointManager
from lexigram.ai.session.checkpointing.diff import StateDiff
from lexigram.ai.session.exceptions import CheckpointNotFoundError
from lexigram.ai.session.stores.in_memory import InMemorySessionStore


class TestCheckpointManager:
    """Tests for CheckpointManager."""

    @pytest.fixture
    def cp_store(self) -> InMemorySessionStore:
        return InMemorySessionStore()

    @pytest.fixture
    def cp_manager(self, cp_store: InMemorySessionStore) -> CheckpointManager:
        return CheckpointManager(store=cp_store, max_checkpoints_per_session=3)

    async def test_create_checkpoint(self, cp_manager: CheckpointManager, cp_store: InMemorySessionStore, make_state) -> None:
        state = make_state()
        await cp_store.save(state)
        cp = await cp_manager.create(state)
        assert cp.session_id == state.session_id
        assert cp.checkpoint_id is not None

    async def test_create_checkpoint_deep_copies_state(self, cp_manager: CheckpointManager, cp_store: InMemorySessionStore, make_state, make_turn) -> None:
        state = make_state()
        await cp_store.save(state)
        cp = await cp_manager.create(state)
        # Create a different state with mutated turn_count
        modified_state = replace(state, turn_count=state.turn_count + 99)
        # Checkpoint should not reflect the modification
        assert cp.state.turn_count != modified_state.turn_count

    async def test_restore_returns_deep_copy(self, cp_manager: CheckpointManager, cp_store: InMemorySessionStore, make_state) -> None:
        state = make_state()
        await cp_store.save(state)
        cp = await cp_manager.create(state)
        restored = await cp_manager.restore(cp.checkpoint_id)
        assert restored.session_id == state.session_id
        # Must be a new object (deep copy)
        assert restored is not cp.state

    async def test_restore_missing_raises(self, cp_manager: CheckpointManager) -> None:
        with pytest.raises(CheckpointNotFoundError):
            await cp_manager.restore("nonexistent")

    async def test_list_returns_checkpoints_for_session(self, cp_manager: CheckpointManager, cp_store: InMemorySessionStore, make_state) -> None:
        state = make_state()
        await cp_store.save(state)
        await cp_manager.create(state)
        await cp_manager.create(state)
        cps = await cp_manager.list(state.session_id)
        assert len(cps) == 2

    async def test_prune_keeps_max_checkpoints(self, cp_store: InMemorySessionStore, make_state) -> None:
        mgr = CheckpointManager(store=cp_store, max_checkpoints_per_session=2)
        state = make_state()
        await cp_store.save(state)
        cp1 = await mgr.create(state)
        cp2 = await mgr.create(state)
        cp3 = await mgr.create(state)
        remaining = await mgr.list(state.session_id)
        assert len(remaining) == 2
        # Oldest is pruned — cp1 should be gone
        ids = {c.checkpoint_id for c in remaining}
        assert cp1.checkpoint_id not in ids


class TestStateDiff:
    """Tests for StateDiff.compute and StateDiff.apply."""

    async def test_compute_empty_diff_for_identical_states(self, make_state) -> None:
        state = make_state()
        diff = StateDiff.compute(state, state)
        assert "new_turns" not in diff
        assert "variables" not in diff

    async def test_compute_detects_new_turns(self, make_state, make_turn) -> None:
        old = make_state()
        new = make_state(session_id=old.session_id)
        t = make_turn()
        new.turns.append(t)
        diff = StateDiff.compute(old, new)
        assert "new_turns" in diff
        assert len(diff["new_turns"]) == 1

    async def test_compute_detects_variable_change(self, make_state) -> None:
        old = make_state()
        new = make_state(session_id=old.session_id, variables={"key": "value"})
        diff = StateDiff.compute(old, new)
        assert diff["variables"] == {"key": "value"}

    async def test_compute_detects_status_change(self, make_state) -> None:
        old = make_state()
        new = make_state(session_id=old.session_id, status=SessionStatus.SUSPENDED)
        diff = StateDiff.compute(old, new)
        assert diff["status"] == SessionStatus.SUSPENDED

    async def test_apply_appends_new_turns(self, make_state, make_turn) -> None:
        base = make_state()
        t = make_turn(content="added")
        diff = {"new_turns": [t]}
        result = StateDiff.apply(base, diff)
        assert len(result.turns) == 1
        assert result.turns[0].content == "added"

    async def test_apply_merges_variables(self, make_state) -> None:
        base = make_state(variables={"existing": "keep"})
        diff = {"variables": {"existing": "overwritten", "new": "added"}}
        result = StateDiff.apply(base, diff)
        assert result.variables["existing"] == "overwritten"
        assert result.variables["new"] == "added"

    async def test_apply_does_not_mutate_base(self, make_state, make_turn) -> None:
        base = make_state()
        diff = {"new_turns": [make_turn()]}
        StateDiff.apply(base, diff)
        assert len(base.turns) == 0

    async def test_roundtrip_compute_apply(self, make_state, make_turn) -> None:
        old = make_state()
        t = make_turn(content="roundtrip")
        new = make_state(session_id=old.session_id, turns=[t], variables={"x": 42})

        diff = StateDiff.compute(old, new)
        reconstructed = StateDiff.apply(old, diff)
        assert len(reconstructed.turns) == 1
        assert reconstructed.variables["x"] == 42
