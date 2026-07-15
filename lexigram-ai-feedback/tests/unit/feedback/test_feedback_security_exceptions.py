"""Unit tests for the security-oriented feedback exception hierarchy."""

from __future__ import annotations

from lexigram.ai.feedback import (
    FeedbackAuthorizationError,
    FeedbackError,
    FeedbackTooLargeError,
    FeedbackValidationError,
)


class TestFeedbackSecurityExceptions:
    """Hierarchy and root-export checks for the new leaf exceptions."""

    def test_feedback_too_large_is_validation_error(self) -> None:
        """FeedbackTooLargeError extends FeedbackValidationError, keeps its code."""
        exc = FeedbackTooLargeError("feedback text exceeds the 10,000-character limit")
        assert isinstance(exc, FeedbackValidationError)
        assert isinstance(exc, FeedbackError)
        assert exc._code == "LEX_ERR_FEED_005"

    def test_feedback_authorization_error_is_feedback_error(self) -> None:
        """FeedbackAuthorizationError extends FeedbackError directly."""
        exc = FeedbackAuthorizationError("caller not authorized for context")
        assert isinstance(exc, FeedbackError)
        assert exc._code == "LEX_ERR_FEED_004"

    def test_message_preserved_as_str(self) -> None:
        """Both exceptions keep the standard Exception str() behavior."""
        assert "boom" in str(FeedbackTooLargeError("boom"))
        assert "nope" in str(FeedbackAuthorizationError("nope"))
