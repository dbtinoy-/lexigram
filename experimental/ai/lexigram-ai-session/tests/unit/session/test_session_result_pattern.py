"""Tests for Result pattern in session manager."""

import pytest
from lexigram.contracts.ai.session import SessionError
from lexigram.ai.session.services.result_pattern_service import SessionManagerWithResultPattern

class TestSessionManagerResultPattern:
    """Test Result pattern in session manager."""

    @pytest.fixture
    def session_manager(self) -> SessionManagerWithResultPattern:
        """Create session manager."""
        return SessionManagerWithResultPattern()

    @pytest.mark.asyncio
    async def test_create_session_returns_ok(self, session_manager):
        """Verify create_session returns Ok."""
        result = await session_manager.create_session("user123")
        assert result.is_ok()
        session_id = result.unwrap()
        assert isinstance(session_id, str)

    @pytest.mark.asyncio
    async def test_create_session_returns_err_for_empty_user(self, session_manager):
        """Verify create_session returns Err for empty user ID."""
        result = await session_manager.create_session("")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SessionError)

    @pytest.mark.asyncio
    async def test_get_session_returns_ok(self, session_manager):
        """Verify get_session returns Ok."""
        result = await session_manager.get_session("session:user123")
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_get_session_returns_err_for_empty_session_id(self, session_manager):
        """Verify get_session returns Err for empty session ID."""
        result = await session_manager.get_session("")
        assert result.is_err()
