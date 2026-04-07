"""Errors for the lexigram-ai-session package."""

from __future__ import annotations

from lexigram.contracts.ai.session import SessionError as _ContractsSessionError


class SessionError(_ContractsSessionError):
    """Base error for all session operations.

    All session-specific exceptions inherit from this class.
    """

    _code: str = "LEX_ERR_SES_006"


class SessionNotFoundError(SessionError):
    """Raised when a session cannot be found by its ID.

    Args:
        session_id: The ID of the session that was not found.
    """

    _code: str = "LEX_ERR_SES_007"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id!r}")


class SessionClosedError(SessionError):
    """Raised when an operation is attempted on a closed session.

    Args:
        session_id: The ID of the closed session.
    """

    _code: str = "LEX_ERR_SES_008"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session is closed and cannot be modified: {session_id!r}")


class SessionExpiredError(SessionError):
    """Raised when an operation is attempted on an expired session.

    Args:
        session_id: The ID of the expired session.
    """

    _code: str = "LEX_ERR_SES_009"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session has expired: {session_id!r}")


class CheckpointNotFoundError(SessionError):
    """Raised when a checkpoint cannot be found by its ID.

    Args:
        checkpoint_id: The ID of the checkpoint that was not found.
    """

    _code: str = "LEX_ERR_SES_010"

    def __init__(self, checkpoint_id: str) -> None:
        self.checkpoint_id = checkpoint_id
        super().__init__(f"Checkpoint not found: {checkpoint_id!r}")


class SessionTransitionError(SessionError):
    """Raised when an invalid state transition is attempted.

    Args:
        session_id: The session ID.
        from_status: Current status.
        to_status: Attempted target status.
    """

    _code: str = "LEX_ERR_SES_011"

    def __init__(self, session_id: str, from_status: str, to_status: str) -> None:
        self.session_id = session_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Invalid transition for session {session_id!r}: "
            f"{from_status!r} → {to_status!r}"
        )


class SessionCapacityError(SessionError):
    """Raised when a session limit is exceeded.

    Args:
        detail: Human-readable description of the exceeded limit.
    """

    _code: str = "LEX_ERR_SES_012"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Session capacity exceeded: {detail}")


__all__ = [
    "CheckpointNotFoundError",
    "SessionCapacityError",
    "SessionClosedError",
    "SessionError",
    "SessionExpiredError",
    "SessionNotFoundError",
    "SessionTransitionError",
]
