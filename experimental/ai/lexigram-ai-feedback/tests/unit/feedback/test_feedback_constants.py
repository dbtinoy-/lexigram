"""Tests for AI Feedback constants."""

import pytest

from lexigram.ai.feedback.constants import (
    DEFAULT_RATING_MAX,
    DEFAULT_RATING_MIN,
    MAX_CONTEXT_SIZE,
    MAX_FEEDBACK_TEXT_LENGTH,
)


class TestFeedbackConstants:
    """Tests for feedback constants values."""

    def test_max_feedback_text_length(self) -> None:
        """Test maximum feedback text length."""
        assert MAX_FEEDBACK_TEXT_LENGTH == 10_000

    def test_default_rating_min(self) -> None:
        """Test default rating minimum."""
        assert DEFAULT_RATING_MIN == 1.0

    def test_default_rating_max(self) -> None:
        """Test default rating maximum."""
        assert DEFAULT_RATING_MAX == 5.0

    def test_max_context_size(self) -> None:
        """Test maximum context size."""
        assert MAX_CONTEXT_SIZE == 50_000


class TestConstantsAllExports:
    """Tests for __all__ exports."""

    def test_all_contains_expected_items(self) -> None:
        """Test that __all__ contains all expected items."""
        from lexigram.ai.feedback import constants

        expected = [
            "DEFAULT_RATING_MAX",
            "DEFAULT_RATING_MIN",
            "MAX_CONTEXT_SIZE",
            "MAX_FEEDBACK_TEXT_LENGTH",
        ]
        for item in expected:
            assert item in constants.__all__
