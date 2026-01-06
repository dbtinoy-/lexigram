"""Unit tests for CacheSessionStore and DatabaseSessionStore."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from lexigram.contracts.ai.session import SessionCheckpoint, SessionStatus
from lexigram.ai.session.stores.cache import CacheSessionStore
from lexigram.ai.session.stores.database import DatabaseSessionStore


@pytest.mark.asyncio
class TestCacheSessionStore:
    """Tests for CacheSessionStore using a mocked cache backend."""

    @pytest.fixture
    def mock_cache(self) -> AsyncMock:
        cache = AsyncMock()
        cache.get.return_value = None
        return cache

    @pytest.fixture
    def store(self, mock_cache: AsyncMock) -> CacheSessionStore:
        return CacheSessionStore(cache=mock_cache)

    async def test_save_persists_to_cache(self, store, mock_cache, make_state) -> None:
        from unittest.mock import ANY
        state = make_state(user_id="u123")
        await store.save(state)
        
        # Verify session save
        mock_cache.set.assert_any_call(
            f"ai:session:{state.session_id}", 
            ANY, 
            ttl=86400
        )
        # Verify user index update
        mock_cache.set.assert_any_call(
            f"ai:session:user:{state.user_id}",
            ANY,
            ttl=86400
        )

    async def test_load_returns_hydrated_state(self, store, mock_cache, make_state) -> None:
        state = make_state()
        # Mock serialised payload
        from lexigram.ai.session.stores.cache import _state_to_dict
        from lexigram.serialization.backends.json import dumps_str
        payload = dumps_str(_state_to_dict(state))
        
        mock_cache.get.return_value = payload
        
        loaded = await store.load(state.session_id)
        assert loaded.session_id == state.session_id
        assert loaded.user_id == state.user_id
        assert loaded.status == state.status

    async def test_load_missing_returns_none(self, store, mock_cache) -> None:
        mock_cache.get.return_value = None
        assert await store.load("missing") is None

    async def test_delete_removes_key(self, store, mock_cache) -> None:
        await store.delete("s1")
        mock_cache.delete.assert_called_with("ai:session:s1")

    async def test_list_sessions_hydrates_multiple(self, store, mock_cache, make_state) -> None:
        s1 = make_state(user_id="u1")
        s2 = make_state(user_id="u1")
        
        from lexigram.ai.session.stores.cache import _state_to_dict
        from lexigram.serialization.backends.json import dumps_str
        
        mock_cache.get.side_effect = [
            dumps_str([s1.session_id, s2.session_id]), # Index
            dumps_str(_state_to_dict(s1)),            # Load s1
            dumps_str(_state_to_dict(s2)),            # Load s2
        ]
        
        results = await store.list_sessions("u1")
        assert len(results) == 2
        assert results[0].session_id == s1.session_id
        assert results[1].session_id == s2.session_id


@pytest.mark.asyncio
class TestDatabaseSessionStore:
    """Tests for DatabaseSessionStore using a mocked database provider."""

    @pytest.fixture
    def mock_conn(self) -> AsyncMock:
        conn = AsyncMock()
        return conn

    @pytest.fixture
    def mock_db(self, mock_conn) -> MagicMock:
        db = MagicMock()
        db.scoped_context.return_value.__aenter__ = AsyncMock()
        db.scoped_context.return_value.__aexit__ = AsyncMock()
        db.get_scoped_connection = AsyncMock(return_value=mock_conn)
        return db

    @pytest.fixture
    def store(self, mock_db: MagicMock) -> DatabaseSessionStore:
        return DatabaseSessionStore(db=mock_db)

    async def test_save_executes_upsert(self, store, mock_conn, make_state) -> None:
        state = make_state()
        await store.save(state)
        
        assert mock_conn.execute.called
        args = mock_conn.execute.call_args[0]
        assert "INSERT INTO ai_sessions" in args[0]
        assert state.session_id in args

    async def test_load_returns_hydrated_state(self, store, mock_conn, make_state) -> None:
        state = make_state()
        # Mock row-like object
        row = {
            "session_id": state.session_id,
            "user_id": state.user_id,
            "status": state.status.value,
            "turns": "[]",
            "metadata": "{}",
            "active_tools": "[]",
            "active_skills": "[]",
            "system_prompt": None,
            "variables": "{}",
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
            "checkpoint_id": None,
            "total_tokens": 0,
            "total_cost": 0.0,
            "turn_count": 0,
            "parent_session_id": None,
            "branch_name": None,
        }
        mock_conn.fetchrow.return_value = row
        
        loaded = await store.load(state.session_id)
        assert loaded.session_id == state.session_id
        assert loaded.user_id == state.user_id

    async def test_delete_executes_delete(self, store, mock_conn) -> None:
        await store.delete("s1")
        mock_conn.execute.assert_called_with(
            "DELETE FROM ai_sessions WHERE session_id = $1", "s1"
        )

    async def test_list_sessions_returns_multiple(self, store, mock_conn, make_state) -> None:
        s1 = make_state(user_id="u1")
        row = {
            "session_id": s1.session_id,
            "user_id": s1.user_id,
            "status": s1.status.value,
            "turns": "[]",
            "metadata": "{}",
            "active_tools": "[]",
            "active_skills": "[]",
            "system_prompt": None,
            "variables": "{}",
            "created_at": s1.created_at.isoformat(),
            "updated_at": s1.updated_at.isoformat(),
            "checkpoint_id": None,
            "total_tokens": 0,
            "total_cost": 0.0,
            "turn_count": 0,
            "parent_session_id": None,
            "branch_name": None,
        }
        mock_conn.fetch.return_value = [row]
        
        results = await store.list_sessions("u1")
        assert len(results) == 1
        assert results[0].session_id == s1.session_id

    async def test_checkpoint_crud(self, store, mock_conn, make_state) -> None:
        state = make_state()
        cp = SessionCheckpoint(
            checkpoint_id="cp1",
            session_id=state.session_id,
            state=state,
            created_at=datetime.now(UTC),
        )
        
        # Save
        await store.save_checkpoint(cp)
        assert mock_conn.execute.called
        
        # Load
        from lexigram.ai.session.stores.cache import _state_to_dict
        from lexigram.serialization.backends.json import dumps_str
        row = {
            "checkpoint_id": cp.checkpoint_id,
            "session_id": cp.session_id,
            "state": dumps_str(_state_to_dict(state)),
            "created_at": cp.created_at.isoformat(),
            "parent_checkpoint_id": None,
            "metadata": "{}",
        }
        mock_conn.fetchrow.return_value = row
        
        loaded = await store.load_checkpoint("cp1")
        assert loaded.checkpoint_id == "cp1"
        
        # Delete
        await store.delete_checkpoint("cp1")
        mock_conn.execute.assert_any_call(
            "DELETE FROM ai_checkpoints WHERE checkpoint_id = $1", "cp1"
        )
