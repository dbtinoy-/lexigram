"""Unit tests for the ContextVar-based SessionContext."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.session.context.session_context import SessionContext
from lexigram.ai.session.exceptions import SessionError
from lexigram.contracts.ai.session import SessionState, SessionStatus


def _make_state(user_id: str = "user1", session_id: str = "sess-1") -> SessionState:
    from datetime import UTC, datetime

    return SessionState(
        session_id=session_id,
        user_id=user_id,
        status=SessionStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestSessionContext:
    """Tests for the ContextVar-backed SessionContext."""

    def test_session_id_raises_when_unbound(self) -> None:
        """session_id raises SessionError when no state is bound."""
        manager = MagicMock()
        ctx = SessionContext(manager=manager)

        with pytest.raises(SessionError):
            _ = ctx.session_id

    def test_state_raises_when_unbound(self) -> None:
        """state raises SessionError when no state is bound."""
        manager = MagicMock()
        ctx = SessionContext(manager=manager)

        with pytest.raises(SessionError):
            _ = ctx.state

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new_session(self) -> None:
        """get_or_create calls manager.create when context is unbound."""
        new_state = _make_state(user_id="u1", session_id="new-sess")
        manager = MagicMock()
        manager.create = AsyncMock(return_value=new_state)

        ctx = SessionContext(manager=manager)
        result = await ctx.get_or_create(user_id="u1")

        assert result is new_state
        manager.create.assert_awaited_once_with(user_id="u1")

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing_without_calling_create_again(
        self,
    ) -> None:
        """get_or_create returns bound state and does not call manager.create."""
        state = _make_state()
        manager = MagicMock()
        manager.create = AsyncMock()

        ctx = SessionContext(manager=manager)
        token = ctx.bind(state)
        try:
            result = await ctx.get_or_create(user_id="u1")

            assert result is state
            manager.create.assert_not_awaited()
        finally:
            ctx.unbind(token)

    def test_bind_unbind_lifecycle(self) -> None:
        """bind makes state accessible; unbind restores unbound state."""
        state = _make_state()
        manager = MagicMock()

        ctx = SessionContext(manager=manager)

        # Before bind — unbound
        with pytest.raises(SessionError):
            _ = ctx.session_id

        token = ctx.bind(state)

        # After bind — accessible
        assert ctx.session_id == state.session_id
        assert ctx.state is state

        ctx.unbind(token)

        # After unbind — unbound again
        with pytest.raises(SessionError):
            _ = ctx.session_id
