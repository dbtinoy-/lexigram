"""Per-request session context — injected by middleware into request scope."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.session.exceptions import SessionError

if TYPE_CHECKING:
    from lexigram.contracts.ai.session import SessionState


class SessionContext:
    """Holds the resolved session for the current request.

    Implements ``SessionContextProtocol``. Injected into request scope by
    ``SessionMiddleware``; consumed directly by controllers or services that
    need to access or update the in-flight session.

    Args:
        session_id: The session ID bound to this context.
        state: The loaded ``SessionState`` for this request.
        manager: The ``SessionManagerImpl`` for performing mutations.
    """

    def __init__(
        self,
        session_id: str,
        state: SessionState,
        manager: Any,
    ) -> None:
        self._session_id = session_id
        self._state = state
        self._manager = manager

    @property
    def session_id(self) -> str:
        """The session ID bound to this request context.

        Returns:
            The current session ID.
        """
        return self._session_id

    @property
    def state(self) -> SessionState:
        """The ``SessionState`` loaded for this request.

        Returns:
            The current session state.

        Raises:
            SessionError: If the context has not been fully initialised.
        """
        if self._state is None:
            raise SessionError("Session context is not bound to a session")
        return self._state

    @property
    def manager(self) -> Any:
        """The session manager for performing mutations.

        Returns:
            The underlying ``SessionManagerImpl``.
        """
        return self._manager

    async def get_or_create(self, user_id: str) -> SessionState:
        """Return the existing session state or create a new session.

        Args:
            user_id: Owner of the session (used only if creating).

        Returns:
            An existing or freshly created ``SessionState``.
        """
        if self._state is not None:
            return self._state
        self._state = await self._manager.create(user_id=user_id)
        self._session_id = self._state.session_id
        return self._state


__all__ = ["SessionContext"]
