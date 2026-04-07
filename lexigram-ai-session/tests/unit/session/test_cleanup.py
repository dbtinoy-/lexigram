"""Unit tests for SessionCleanupScheduler."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.session.config import SessionConfig
from lexigram.ai.session.manager.cleanup import SessionCleanupScheduler


@pytest.fixture
def mock_manager() -> MagicMock:
    m = MagicMock()
    m.close = AsyncMock()
    return m


@pytest.fixture
def mock_store() -> MagicMock:
    s = MagicMock()
    s.list_all_active = AsyncMock(return_value=[])
    return s


class TestSessionCleanupScheduler:
    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, mock_manager: MagicMock) -> None:
        config = SessionConfig(cleanup_interval_s=1)
        scheduler = SessionCleanupScheduler(mock_manager, config)
        
        # Override to prevent infinite loop hanging tests
        scheduler._cleanup_loop = AsyncMock()  # type: ignore[method-assign]
        
        assert not scheduler._running
        await scheduler.start()
        assert scheduler._running
        
        # Starting again should be a no-op
        await scheduler.start()
        
        await scheduler.stop()
        assert not scheduler._running

    @pytest.mark.asyncio
    async def test_run_cleanup_pass_with_ttl_disabled(
        self, mock_manager: MagicMock
    ) -> None:
        config = SessionConfig(session_ttl=0)
        scheduler = SessionCleanupScheduler(mock_manager, config)
        
        closed = await scheduler.run_cleanup_pass()
        assert closed == 0
        mock_manager.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_cleanup_pass_closes_expired(
        self, mock_manager: MagicMock, mock_store: MagicMock
    ) -> None:
        # Mocking the injected store on the manager
        mock_manager._store = mock_store
        
        # Two sessions: one expired, one active
        now = datetime.now(UTC)
        expired = MagicMock()
        expired.session_id = "expired_id"
        expired.updated_at = now - timedelta(hours=48)
        
        active = MagicMock()
        active.session_id = "active_id"
        active.updated_at = now - timedelta(minutes=10)
        
        mock_store.list_all_active = AsyncMock(return_value=[expired, active])
        
        config = SessionConfig(session_ttl=86400)  # 24 hours
        scheduler = SessionCleanupScheduler(mock_manager, config)
        
        closed = await scheduler.run_cleanup_pass()
        
        assert closed == 1
        mock_manager.close.assert_awaited_once_with("expired_id")
        
    @pytest.mark.asyncio
    async def test_run_cleanup_pass_swallows_close_errors(
        self, mock_manager: MagicMock, mock_store: MagicMock
    ) -> None:
        mock_manager._store = mock_store
        
        now = datetime.now(UTC)
        expired = MagicMock()
        expired.session_id = "expired_id"
        expired.updated_at = now - timedelta(hours=48)
        
        mock_store.list_all_active = AsyncMock(return_value=[expired])
        # Force an error when closing to ensure it doesn't crash the loop
        mock_manager.close.side_effect = Exception("DB Connection Lost")
        
        config = SessionConfig(session_ttl=86400)
        scheduler = SessionCleanupScheduler(mock_manager, config)
        
        closed = await scheduler.run_cleanup_pass()
        
        assert closed == 0
        mock_manager.close.assert_awaited()
