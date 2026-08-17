"""Unit tests for BranchManager and merge strategies."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from lexigram.contracts.ai.session import SessionState, SessionStatus, SessionTurn
from lexigram.ai.session.branching.branch_manager import BranchManager
from lexigram.ai.session.branching.merge import AppendMerge, SelectiveMerge
from lexigram.ai.session.exceptions import (
    CheckpointNotFoundError,
    SessionCapacityError,
    SessionNotFoundError,
)
from lexigram.ai.session.stores.in_memory import InMemorySessionStore


@pytest.fixture
def branch_store() -> InMemorySessionStore:
    return InMemorySessionStore()


@pytest.fixture
def branch_manager(branch_store: InMemorySessionStore) -> BranchManager:
    return BranchManager(store=branch_store, max_branches_per_session=5)


class TestBranchManagerFork:
    """Tests for BranchManager.fork."""

    async def test_fork_creates_new_session(self, branch_manager, branch_store, make_state) -> None:
        state = make_state()
        await branch_store.save(state)
        branch = await branch_manager.fork(state.session_id, "alt")
        assert branch.session_id != state.session_id

    async def test_fork_sets_parent_session_id(self, branch_manager, branch_store, make_state) -> None:
        state = make_state()
        await branch_store.save(state)
        branch = await branch_manager.fork(state.session_id, "alt")
        assert branch.parent_session_id == state.session_id

    async def test_fork_sets_branch_name(self, branch_manager, branch_store, make_state) -> None:
        state = make_state()
        await branch_store.save(state)
        branch = await branch_manager.fork(state.session_id, "my-branch")
        assert branch.branch_name == "my-branch"

    async def test_fork_copies_turns(self, branch_manager, branch_store, make_state, make_turn) -> None:
        state = make_state()
        t = make_turn(content="original turn")
        state.turns.append(t)
        await branch_store.save(state)
        branch = await branch_manager.fork(state.session_id, "copy")
        assert len(branch.turns) == 1
        assert branch.turns[0].content == "original turn"

    async def test_fork_deep_copies_turns(self, branch_manager, branch_store, make_state, make_turn) -> None:
        state = make_state()
        t = make_turn()
        state.turns.append(t)
        await branch_store.save(state)
        branch = await branch_manager.fork(state.session_id, "copy")
        # Mutating branch turns should not affect original
        branch.turns.clear()
        reloaded = await branch_store.load(state.session_id)
        assert len(reloaded.turns) == 1

    async def test_fork_missing_session_raises(self, branch_manager) -> None:
        with pytest.raises(SessionNotFoundError):
            await branch_manager.fork("nonexistent", "alt")

    async def test_fork_from_checkpoint(self, branch_manager, branch_store, make_state) -> None:
        from lexigram.contracts.ai.session import SessionCheckpoint
        state = make_state()
        await branch_store.save(state)
        cp = SessionCheckpoint(
            checkpoint_id=str(uuid4()),
            session_id=state.session_id,
            state=state,
            created_at=datetime.now(UTC),
        )
        await branch_store.save_checkpoint(cp)
        branch = await branch_manager.fork(state.session_id, "from-cp", from_checkpoint=cp.checkpoint_id)
        assert branch.session_id != state.session_id

    async def test_fork_from_missing_checkpoint_raises(self, branch_manager, branch_store, make_state) -> None:
        state = make_state()
        await branch_store.save(state)
        with pytest.raises(CheckpointNotFoundError):
            await branch_manager.fork(state.session_id, "alt", from_checkpoint="bad-id")


class TestBranchManagerMerge:
    """Tests for BranchManager.merge."""

    async def test_merge_appends_branch_turns_by_default(
        self, branch_manager, branch_store, make_state, make_turn
    ) -> None:
        parent_turn = make_turn(content="parent turn")
        parent = make_state(user_id="u1", turns=[parent_turn])
        await branch_store.save(parent)

        branch_turn = SessionTurn(
            turn_id=str(uuid4()),
            role="assistant",
            content="branch turn",
            timestamp=parent_turn.timestamp + timedelta(seconds=1),
        )
        branch = make_state(user_id="u1", turns=[parent_turn, branch_turn])
        branch = replace(branch, parent_session_id=parent.session_id)
        await branch_store.save(branch)

        merged = await branch_manager.merge(parent.session_id, branch.session_id)
        contents = [t.content for t in merged.turns]
        assert "parent turn" in contents
        assert "branch turn" in contents

    async def test_merge_missing_parent_raises(self, branch_manager, branch_store, make_state) -> None:
        branch = make_state()
        await branch_store.save(branch)
        with pytest.raises(SessionNotFoundError):
            await branch_manager.merge("nonexistent", branch.session_id)

    async def test_merge_missing_branch_raises(self, branch_manager, branch_store, make_state) -> None:
        parent = make_state()
        await branch_store.save(parent)
        with pytest.raises(SessionNotFoundError):
            await branch_manager.merge(parent.session_id, "nonexistent")

    async def test_merge_with_selective_strategy(
        self, branch_manager, branch_store, make_state, make_turn
    ) -> None:
        parent = make_state(user_id="u1")
        await branch_store.save(parent)

        t1 = make_turn(content="keep me")
        t2 = make_turn(content="ignore me")
        branch = make_state(user_id="u1", turns=[t1, t2])
        await branch_store.save(branch)

        strategy = SelectiveMerge(turn_ids=[t1.turn_id])
        merged = await branch_manager.merge(parent.session_id, branch.session_id, strategy=strategy)
        contents = [t.content for t in merged.turns]
        assert "keep me" in contents
        assert "ignore me" not in contents


class TestAppendMerge:
    """Direct tests for AppendMerge strategy."""

    async def test_appends_only_new_turns(self, make_state, make_turn) -> None:
        shared_turn = make_turn(content="shared")
        parent = make_state(turns=[shared_turn])

        new_turn = SessionTurn(
            turn_id=str(uuid4()),
            role="assistant",
            content="new in branch",
            timestamp=shared_turn.timestamp + timedelta(seconds=1),
        )
        branch = make_state(session_id=parent.session_id, turns=[shared_turn, new_turn])

        merged = await AppendMerge().merge(parent, branch)
        assert len(merged.turns) == 2
        assert merged.turns[-1].content == "new in branch"

    async def test_merges_variables(self, make_state) -> None:
        parent = make_state()
        parent.variables["a"] = 1
        branch = make_state(session_id=parent.session_id)
        branch.variables["b"] = 2

        merged = await AppendMerge().merge(parent, branch)
        assert merged.variables["a"] == 1
        assert merged.variables["b"] == 2


class TestSelectiveMerge:
    """Direct tests for SelectiveMerge strategy."""

    async def test_only_selected_turn_ids_merged(self, make_state, make_turn) -> None:
        parent = make_state()
        t1 = make_turn(content="selected")
        t2 = make_turn(content="not selected")
        branch = make_state(session_id=parent.session_id, turns=[t1, t2])

        merged = await SelectiveMerge(turn_ids=[t1.turn_id]).merge(parent, branch)
        assert len(merged.turns) == 1
        assert merged.turns[0].content == "selected"

    async def test_empty_selection_produces_no_new_turns(self, make_state, make_turn) -> None:
        parent = make_state()
        branch = make_state(session_id=parent.session_id, turns=[make_turn()])
        merged = await SelectiveMerge(turn_ids=[]).merge(parent, branch)
        assert len(merged.turns) == 0
