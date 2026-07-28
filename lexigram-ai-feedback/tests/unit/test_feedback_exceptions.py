"""Tests for feedback exceptions."""

from __future__ import annotations

import pytest

from lexigram.ai.feedback.exceptions import (
    FeedbackError,
    FeedbackProcessingError,
    FeedbackValidationError,
)


class TestFeedbackError:
    """Tests for FeedbackError base exception."""

    def test_feedback_error_inherits_from_ai_error(self) -> None:
        """Verify FeedbackError inherits from AIError."""
        from lexigram.contracts.ai.exceptions import AIError

        assert issubclass(FeedbackError, AIError)

    def test_feedback_error_can_be_instantiated(self) -> None:
        """Verify FeedbackError can be raised with a message."""
        error = FeedbackError("Test error message")
        assert "Test error message" in str(error)

    def test_feedback_error_is_exception_subclass(self) -> None:
        """Verify FeedbackError is an Exception subclass."""
        assert issubclass(FeedbackError, Exception)

    def test_feedback_error_default_message(self) -> None:
        """Verify FeedbackError can be instantiated without message."""
        error = FeedbackError()
        assert isinstance(error, FeedbackError)


class TestFeedbackProcessingError:
    """Tests for FeedbackProcessingError exception."""

    def test_feedback_processing_error_inherits_from_feedback_error(
        self,
    ) -> None:
        """Verify FeedbackProcessingError inherits from FeedbackError."""
        assert issubclass(FeedbackProcessingError, FeedbackError)

    def test_feedback_processing_error_can_be_instantiated(self) -> None:
        """Verify FeedbackProcessingError can be raised."""
        error = FeedbackProcessingError("Processing failed")
        assert "Processing failed" in str(error)

    def test_feedback_processing_error_is_feedback_error(self) -> None:
        """Verify FeedbackProcessingError can be caught as FeedbackError."""
        error = FeedbackProcessingError("test")
        assert isinstance(error, FeedbackError)

    def test_feedback_processing_error_chaining(self) -> None:
        """Verify FeedbackProcessingError supports exception chaining."""
        original_error = ValueError("Original cause")
        error = FeedbackProcessingError("Processing failed")
        error.__cause__ = original_error
        assert error.__cause__ is original_error


class TestFeedbackValidationError:
    """Tests for FeedbackValidationError exception."""

    def test_feedback_validation_error_inherits_from_feedback_error(
        self,
    ) -> None:
        """Verify FeedbackValidationError inherits from FeedbackError."""
        assert issubclass(FeedbackValidationError, FeedbackError)

    def test_feedback_validation_error_can_be_instantiated(self) -> None:
        """Verify FeedbackValidationError can be raised."""
        error = FeedbackValidationError("Invalid feedback data")
        assert "Invalid feedback data" in str(error)

    def test_feedback_validation_error_is_feedback_error(self) -> None:
        """Verify FeedbackValidationError can be caught as FeedbackError."""
        error = FeedbackValidationError("test")
        assert isinstance(error, FeedbackError)

    def test_feedback_validation_error_chaining(self) -> None:
        """Verify FeedbackValidationError supports exception chaining."""
        original_error = ValueError("Original cause")
        error = FeedbackValidationError("Validation failed")
        error.__cause__ = original_error
        assert error.__cause__ is original_error


class TestExceptionHierarchy:
    """Test exception hierarchy and catchability."""

    def test_feedback_processing_error_cannot_be_caught_as_validation_error(
        self,
    ) -> None:
        """Verify FeedbackProcessingError is not caught by FeedbackValidationError."""
        error = FeedbackProcessingError("test")
        with pytest.raises(FeedbackProcessingError):
            raise error

    def test_feedback_validation_error_cannot_be_caught_as_processing_error(
        self,
    ) -> None:
        """Verify FeedbackValidationError is not caught by FeedbackProcessingError."""
        error = FeedbackValidationError("test")
        with pytest.raises(FeedbackValidationError):
            raise error

    def test_all_feedback_errors_can_be_caught_as_feedback_error(self) -> None:
        """Verify all feedback errors can be caught as FeedbackError."""
        processing_error = FeedbackProcessingError("test1")
        validation_error = FeedbackValidationError("test2")

        with pytest.raises(FeedbackError):
            raise processing_error

        with pytest.raises(FeedbackError):
            raise validation_error

    def test_feedback_error_cannot_be_caught_as_processing_error(self) -> None:
        """Verify FeedbackError base cannot be caught as processing."""
        error = FeedbackError("base error")
        with pytest.raises(FeedbackError):
            raise error


class TestExceptionMessages:
    """Test exception message content."""

    def test_feedback_error_message_content(self) -> None:
        """Verify FeedbackError message is preserved."""
        msg = "Feedback operation failed: cannot connect to storage"
        error = FeedbackError(msg)
        assert msg in str(error)

    def test_feedback_processing_error_message_content(self) -> None:
        """Verify FeedbackProcessingError message is preserved."""
        msg = "Failed to process feedback batch"
        error = FeedbackProcessingError(msg)
        assert msg in str(error)

    def test_feedback_validation_error_message_content(self) -> None:
        """Verify FeedbackValidationError message is preserved."""
        msg = "Feedback value exceeds maximum length"
        error = FeedbackValidationError(msg)
        assert msg in str(error)