"""Session state machine — validates and executes status transitions."""

from __future__ import annotations

from lexigram.ai.session.exceptions import SessionTransitionError

# Allowed transitions: from_status -> set of allowed to_statuses
_TRANSITIONS: dict[str, set[str]] = {
    "active": {"suspended", "closed"},
    "suspended": {"active", "closed"},
    "closed": set(),
    "expired": set(),
}


class SessionStateMachine:
    """Validates and enforces session lifecycle status transitions.

    Encodes the allowed state graph:
    - ACTIVE  → SUSPENDED or CLOSED
    - SUSPENDED → ACTIVE or CLOSED
    - CLOSED / EXPIRED → terminal (no transitions allowed)
    """

    def validate(self, session_id: str, from_status: str, to_status: str) -> None:
        """Assert that a transition is allowed, raise otherwise.

        Args:
            session_id: The session being transitioned (for error messages).
            from_status: Current status string.
            to_status: Desired target status string.

        Raises:
            SessionTransitionError: If the transition is not permitted.
        """
        allowed = _TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise SessionTransitionError(session_id, from_status, to_status)

    def can_transition(self, from_status: str, to_status: str) -> bool:
        """Return True if the transition from *from_status* to *to_status* is valid.

        Args:
            from_status: Current status string.
            to_status: Desired target status string.

        Returns:
            True when the transition is allowed.
        """
        return to_status in _TRANSITIONS.get(from_status, set())

    def is_terminal(self, status: str) -> bool:
        """Return True if the given status is a terminal (no-exit) state.

        Args:
            status: Status string to check.

        Returns:
            True for ``closed`` and ``expired``.
        """
        return not _TRANSITIONS.get(status)


__all__ = ["SessionStateMachine"]
