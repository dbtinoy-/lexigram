"""Tests for AI Feedback exceptions."""

import pytest

from lexigram.ai.feedback.exceptions import (
    FeedbackError,
    FeedbackProcessingError,
    FeedbackValidationError,
)


class TestFeedbackError:
    """Tests for FeedbackError base exception."""

    def test_feedback_error_is_exception(self) -> None:
        """Test FeedbackError is an exception."""
        error = FeedbackError("test error")
        assert isinstance(error, Exception)

    def test_feedback_error_message(self) -> None:
        """Test FeedbackError stores message."""
        error = FeedbackError("test message")
        assert "test message" in str(error)


class TestFeedbackProcessingError:
    """Tests for FeedbackProcessingError."""

    def test_feedback_processing_error_inherits_from_feedback_error(self) -> None:
        """Test FeedbackProcessingError inherits from FeedbackError."""
        error = FeedbackProcessingError("processing failed")
        assert isinstance(error, FeedbackError)

    def test_feedback_processing_error_message(self) -> None:
        """Test FeedbackProcessingError stores message."""
        error = FeedbackProcessingError("processing failed")
        assert "processing failed" in str(error)


class TestFeedbackValidationError:
    """Tests for FeedbackValidationError."""

    def test_feedback_validation_error_inherits_from_feedback_error(self) -> None:
        """Test FeedbackValidationError inherits from FeedbackError."""
        error = FeedbackValidationError("validation failed")
        assert isinstance(error, FeedbackError)

    def test_feedback_validation_error_message(self) -> None:
        """Test FeedbackValidationError stores message."""
        error = FeedbackValidationError("invalid rating")
        assert "invalid rating" in str(error)


class TestExceptionsAllExports:
    """Tests for __all__ exports."""

    def test_all_contains_expected_exceptions(self) -> None:
        """Test that __all__ contains all expected exceptions."""
        from lexigram.ai.feedback import exceptions

        expected = [
            "FeedbackError",
            "FeedbackProcessingError",
            "FeedbackValidationError",
        ]
        for exc in expected:
            assert exc in exceptions.__all__
