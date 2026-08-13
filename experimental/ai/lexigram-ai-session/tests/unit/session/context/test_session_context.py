"""Unit tests for SessionContext."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.session.context.core import SessionContext


class TestSessionContext:
    """Tests for SessionContext class."""

    async def test_get_or_create_with_existing(self, make_state) -> None:
        """Returns existing session when state is not None."""
        existing_state = make_state()
        mock_manager = MagicMock()

        context = SessionContext(
            session_id=existing_state.session_id,
            state=existing_state,
            manager=mock_manager,
        )

        result = await context.get_or_create(user_id="user1")

        assert result is existing_state
        mock_manager.create.assert_not_called()

    async def test_get_or_create_with_none(self, make_state) -> None:
        """Creates new session when state is None."""
        new_state = make_state(user_id="user1")
        mock_manager = MagicMock()
        mock_manager.create = AsyncMock(return_value=new_state)

        context = SessionContext(
            session_id="",
            state=None,
            manager=mock_manager,
        )

        result = await context.get_or_create(user_id="user1")

        assert result is new_state
        assert context._session_id == new_state.session_id
        mock_manager.create.assert_called_once_with(user_id="user1")

    async def test_session_id_property(self, make_state) -> None:
        """session_id property returns bound session ID."""
        state = make_state()
        mock_manager = MagicMock()

        context = SessionContext(
            session_id=state.session_id,
            state=state,
            manager=mock_manager,
        )

        assert context.session_id == state.session_id

    async def test_state_property_returns_state(self, make_state) -> None:
        """state property returns the current session state."""
        state = make_state()
        mock_manager = MagicMock()

        context = SessionContext(
            session_id=state.session_id,
            state=state,
            manager=mock_manager,
        )

        assert context.state is state

    async def test_state_property_raises_when_none(self) -> None:
        """state property raises when state is None."""
        from lexigram.ai.session.exceptions import SessionError

        mock_manager = MagicMock()

        context = SessionContext(
            session_id="",
            state=None,
            manager=mock_manager,
        )

        with pytest.raises(SessionError):
            _ = context.state

    def test_manager_property(self, make_state) -> None:
        """manager property returns the session manager."""
        state = make_state()
        mock_manager = MagicMock()

        context = SessionContext(
            session_id=state.session_id,
            state=state,
            manager=mock_manager,
        )

        assert context.manager is mock_manager


class TestSessionContextLifecycle:
    """Tests for session context lifecycle management."""

    async def test_context_manager_enter_creates_state(self, make_state) -> None:
        """Entering context with None state creates new session."""
        new_state = make_state(user_id="user1")
        mock_manager = MagicMock()
        mock_manager.create = AsyncMock(return_value=new_state)

        context = SessionContext(
            session_id="",
            state=None,
            manager=mock_manager,
        )

        result = await context.get_or_create(user_id="user1")

        assert result is not None
        assert result.session_id == new_state.session_id
        mock_manager.create.assert_called_once_with(user_id="user1")

    async def test_context_manager_exit_clears_state(self, make_state) -> None:
        """Exiting context clears the session state."""
        state = make_state()
        mock_manager = MagicMock()

        context = SessionContext(
            session_id=state.session_id,
            state=state,
            manager=mock_manager,
        )

        context._state = None
        context._session_id = ""

        assert context._state is None
        assert context._session_id == ""
