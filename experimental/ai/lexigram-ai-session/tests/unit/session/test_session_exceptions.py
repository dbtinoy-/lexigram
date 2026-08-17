"""Unit tests for session exceptions."""

from __future__ import annotations

import pytest


class TestSessionExceptions:
    """Test session exception classes."""

    def test_session_error_base(self) -> None:
        """Verify SessionError is the base exception."""
        from lexigram.ai.session.exceptions import SessionError

        with pytest.raises(SessionError):
            raise SessionError("test error")

    def test_session_not_found_error(self) -> None:
        """Verify SessionNotFoundError with correct attributes."""
        from lexigram.ai.session.exceptions import SessionNotFoundError

        exc = SessionNotFoundError("sess-123")
        assert exc.session_id == "sess-123"
        assert "sess-123" in str(exc)

    def test_session_closed_error(self) -> None:
        """Verify SessionClosedError with correct attributes."""
        from lexigram.ai.session.exceptions import SessionClosedError

        exc = SessionClosedError("sess-456")
        assert exc.session_id == "sess-456"
        assert "closed" in str(exc).lower()

    def test_session_expired_error(self) -> None:
        """Verify SessionExpiredError with correct attributes."""
        from lexigram.ai.session.exceptions import SessionExpiredError

        exc = SessionExpiredError("sess-789")
        assert exc.session_id == "sess-789"
        assert "expired" in str(exc).lower()

    def test_checkpoint_not_found_error(self) -> None:
        """Verify CheckpointNotFoundError with correct attributes."""
        from lexigram.ai.session.exceptions import CheckpointNotFoundError

        exc = CheckpointNotFoundError("cp-999")
        assert exc.checkpoint_id == "cp-999"
        assert "cp-999" in str(exc)

    def test_session_transition_error(self) -> None:
        """Verify SessionTransitionError with correct attributes."""
        from lexigram.ai.session.exceptions import SessionTransitionError

        exc = SessionTransitionError("sess-111", "active", "closed")
        assert exc.session_id == "sess-111"
        assert exc.from_status == "active"
        assert exc.to_status == "closed"
        assert "active" in str(exc)
        assert "closed" in str(exc)

    def test_session_capacity_error(self) -> None:
        """Verify SessionCapacityError with correct message."""
        from lexigram.ai.session.exceptions import SessionCapacityError

        exc = SessionCapacityError("max sessions reached")
        assert "capacity exceeded" in str(exc).lower()
        assert "max sessions" in str(exc).lower()


class TestSessionExceptionsInheritance:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_session_error(self) -> None:
        """Verify all session exceptions inherit from SessionError."""
        from lexigram.ai.session.exceptions import (
            CheckpointNotFoundError,
            SessionCapacityError,
            SessionClosedError,
            SessionError,
            SessionExpiredError,
            SessionNotFoundError,
            SessionTransitionError,
        )

        assert issubclass(SessionNotFoundError, SessionError)
        assert issubclass(SessionClosedError, SessionError)
        assert issubclass(SessionExpiredError, SessionError)
        assert issubclass(CheckpointNotFoundError, SessionError)
        assert issubclass(SessionTransitionError, SessionError)
        assert issubclass(SessionCapacityError, SessionError)


class TestSessionExceptionsExports:
    """Test that exceptions are properly exported."""

    def test_exceptions_exported(self) -> None:
        """Verify all exceptions are in __all__."""
        from lexigram.ai.session import exceptions

        assert "SessionError" in exceptions.__all__
        assert "SessionNotFoundError" in exceptions.__all__
        assert "SessionClosedError" in exceptions.__all__
        assert "SessionExpiredError" in exceptions.__all__
        assert "CheckpointNotFoundError" in exceptions.__all__
        assert "SessionTransitionError" in exceptions.__all__
        assert "SessionCapacityError" in exceptions.__all__