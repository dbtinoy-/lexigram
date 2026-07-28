"""Per-request session context using contextvars for task-scoped isolation."""

from __future__ import annotations

import contextvars

from lexigram.ai.session.exceptions import SessionError
from lexigram.contracts.ai.session import SessionManagerProtocol, SessionState

_SESSION_STATE: contextvars.ContextVar[SessionState | None] = contextvars.ContextVar(
    "lexigram_session_state", default=None
)


class SessionContext:
    """Per-request session context backed by a ``ContextVar``.

    Implements ``SessionContextProtocol``. Each asyncio task (request) has
    its own isolated slot in ``_SESSION_STATE``; no cross-request leakage
    occurs even under high concurrency.

    The typical lifecycle inside a request middleware is::

        token = ctx.bind(state)       # request start
        try:
            ...                       # handle request
        finally:
            ctx.unbind(token)         # request end

    Args:
        manager: Session lifecycle manager used by ``get_or_create``.
    """

    def __init__(self, manager: SessionManagerProtocol) -> None:
        self._manager = manager

    @property
    def session_id(self) -> str:
        """Current session ID from the task-scoped context variable.

        Returns:
            The bound session ID.

        Raises:
            SessionError: If no session has been bound for this task.
        """
        state = _SESSION_STATE.get()
        if state is None:
            raise SessionError("No session is currently bound to this context")
        return state.session_id

    @property
    def state(self) -> SessionState:
        """Current session state from the task-scoped context variable.

        Returns:
            The bound ``SessionState``.

        Raises:
            SessionError: If no session has been bound for this task.
        """
        state = _SESSION_STATE.get()
        if state is None:
            raise SessionError("No session is currently bound to this context")
        return state

    async def get_or_create(self, user_id: str) -> SessionState:
        """Return the bound session, or create a new one if unbound.

        Args:
            user_id: Owner of the session (only used when creating).

        Returns:
            An existing or freshly created ``SessionState``.
        """
        state = _SESSION_STATE.get()
        if state is not None:
            return state
        new_state = await self._manager.create(user_id=user_id)
        _SESSION_STATE.set(new_state)
        return new_state

    def bind(self, state: SessionState) -> contextvars.Token[SessionState | None]:
        """Bind a session state to the current asyncio task.

        Should be called at the start of a request by middleware.

        Args:
            state: The ``SessionState`` to bind.

        Returns:
            A ``Token`` that must be passed to ``unbind`` to restore the
            previous context value.
        """
        return _SESSION_STATE.set(state)

    def unbind(self, token: contextvars.Token[SessionState | None]) -> None:
        """Restore the context variable to its pre-bind value.

        Should be called at the end of a request (in a ``finally`` block)
        by middleware.

        Args:
            token: The token returned by the corresponding ``bind`` call.
        """
        _SESSION_STATE.reset(token)


__all__ = ["SessionContext"]
