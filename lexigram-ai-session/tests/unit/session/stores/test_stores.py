"""Unit tests for InMemorySessionStore."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from lexigram.contracts.ai.session import (
    SessionCheckpoint,
    SessionState,
    SessionStatus,
    SessionTurn,
)
from lexigram.ai.session.stores.in_memory import InMemorySessionStore


class TestInMemorySessionStoreCRUD:
    """Test basic save/load/delete/list operations."""

    async def test_save_and_load_returns_state(self, make_state) -> None:
        store = InMemorySessionStore()
        state = make_state(user_id="u1")
        await store.save(state)
        loaded = await store.load(state.session_id)
        assert loaded is state

    async def test_load_missing_returns_none(self) -> None:
        store = InMemorySessionStore()
        assert await store.load("nonexistent") is None

    async def test_save_overwrites_existing(self, make_state) -> None:
        store = InMemorySessionStore()
        state = make_state()
        await store.save(state)
        state = replace(state, status=SessionStatus.SUSPENDED)
        await store.save(state)
        loaded = await store.load(state.session_id)
        assert loaded.status == SessionStatus.SUSPENDED

    async def test_delete_removes_state(self, make_state) -> None:
        store = InMemorySessionStore()
        state = make_state()
        await store.save(state)
        await store.delete(state.session_id)
        assert await store.load(state.session_id) is None

    async def test_delete_nonexistent_is_noop(self) -> None:
        store = InMemorySessionStore()
        # Must not raise
        await store.delete("nonexistent")

    async def test_list_sessions_filters_by_user(self, make_state) -> None:
        store = InMemorySessionStore()
        s1 = make_state(user_id="alice")
        s2 = make_state(user_id="alice")
        s3 = make_state(user_id="bob")
        for s in (s1, s2, s3):
            await store.save(s)

        alice_sessions = await store.list_sessions("alice")
        assert len(alice_sessions) == 2
        assert {s.session_id for s in alice_sessions} == {s1.session_id, s2.session_id}

    async def test_list_sessions_empty_for_unknown_user(self) -> None:
        store = InMemorySessionStore()
        assert await store.list_sessions("nobody") == []


class TestInMemorySessionStoreCheckpoints:
    """Test checkpoint CRUD."""

    def _make_checkpoint(self, state: SessionState) -> SessionCheckpoint:
        return SessionCheckpoint(
            checkpoint_id=str(uuid4()),
            session_id=state.session_id,
            state=state,
            created_at=datetime.now(UTC),
        )

    async def test_save_and_load_checkpoint(self, make_state) -> None:
        store = InMemorySessionStore()
        state = make_state()
        cp = self._make_checkpoint(state)
        await store.save_checkpoint(cp)
        loaded = await store.load_checkpoint(cp.checkpoint_id)
        assert loaded is cp

    async def test_load_missing_checkpoint_returns_none(self) -> None:
        store = InMemorySessionStore()
        assert await store.load_checkpoint("missing") is None

    async def test_list_checkpoints_filters_by_session(self, make_state) -> None:
        store = InMemorySessionStore()
        s1 = make_state()
        s2 = make_state()
        cp1 = self._make_checkpoint(s1)
        cp2 = self._make_checkpoint(s1)
        cp3 = self._make_checkpoint(s2)
        for cp in (cp1, cp2, cp3):
            await store.save_checkpoint(cp)

        s1_cps = await store.list_checkpoints(s1.session_id)
        assert len(s1_cps) == 2
        assert {c.checkpoint_id for c in s1_cps} == {cp1.checkpoint_id, cp2.checkpoint_id}

    async def test_list_checkpoints_sorted_by_created_at(self, make_state) -> None:
        store = InMemorySessionStore()
        state = make_state()

        now = datetime.now(UTC)
        cp_older = SessionCheckpoint(
            checkpoint_id=str(uuid4()),
            session_id=state.session_id,
            state=state,
            created_at=now - timedelta(seconds=10),
        )
        cp_newer = SessionCheckpoint(
            checkpoint_id=str(uuid4()),
            session_id=state.session_id,
            state=state,
            created_at=now,
        )
        await store.save_checkpoint(cp_newer)
        await store.save_checkpoint(cp_older)

        cps = await store.list_checkpoints(state.session_id)
        assert cps[0].checkpoint_id == cp_older.checkpoint_id
        assert cps[1].checkpoint_id == cp_newer.checkpoint_id

    async def test_delete_checkpoint(self, make_state) -> None:
        store = InMemorySessionStore()
        state = make_state()
        cp = self._make_checkpoint(state)
        await store.save_checkpoint(cp)
        await store.delete_checkpoint(cp.checkpoint_id)
        assert await store.load_checkpoint(cp.checkpoint_id) is None

    async def test_delete_nonexistent_checkpoint_is_noop(self) -> None:
        store = InMemorySessionStore()
        await store.delete_checkpoint("nonexistent")


class TestInMemorySessionStoreExpiry:
    """Test TTL-based session expiry."""

    async def test_expire_old_sessions_removes_stale(self, make_state) -> None:
        store = InMemorySessionStore()
        old_state = make_state()
        old_state = replace(old_state, updated_at=datetime.now(UTC) - timedelta(seconds=3600))
        await store.save(old_state)

        fresh_state = make_state()
        await store.save(fresh_state)

        expired = await store.expire_old_sessions(ttl_seconds=60)
        assert expired == 1
        assert await store.load(old_state.session_id) is None
        assert await store.load(fresh_state.session_id) is not None

    async def test_expire_returns_zero_when_nothing_stale(self, make_state) -> None:
        store = InMemorySessionStore()
        state = make_state()
        await store.save(state)
        expired = await store.expire_old_sessions(ttl_seconds=9999)
        assert expired == 0
