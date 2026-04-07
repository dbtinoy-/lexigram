"""Tests for feedback constants."""

from __future__ import annotations

import pytest

from lexigram.ai.feedback import constants


class TestConstants:
    """Tests for feedback constants."""

    def test_env_prefix(self) -> None:
        """Verify ENV_PREFIX is correct."""
        assert constants.ENV_PREFIX == "LEX_AI_FEEDBACK__"

    def test_env_nested_delimiter(self) -> None:
        """Verify ENV_NESTED_DELIMITER is correct."""
        assert constants.ENV_NESTED_DELIMITER == "__"

    def test_max_feedback_text_length(self) -> None:
        """Verify MAX_FEEDBACK_TEXT_LENGTH is correct."""
        assert constants.MAX_FEEDBACK_TEXT_LENGTH == 10_000
        assert isinstance(constants.MAX_FEEDBACK_TEXT_LENGTH, int)

    def test_default_rating_min(self) -> None:
        """Verify DEFAULT_RATING_MIN is correct."""
        assert constants.DEFAULT_RATING_MIN == 1.0
        assert isinstance(constants.DEFAULT_RATING_MIN, float)

    def test_default_rating_max(self) -> None:
        """Verify DEFAULT_RATING_MAX is correct."""
        assert constants.DEFAULT_RATING_MAX == 5.0
        assert isinstance(constants.DEFAULT_RATING_MAX, float)

    def test_max_context_size(self) -> None:
        """Verify MAX_CONTEXT_SIZE is correct."""
        assert constants.MAX_CONTEXT_SIZE == 50_000
        assert isinstance(constants.MAX_CONTEXT_SIZE, int)

    def test_version_is_string(self) -> None:
        """Verify __version__ is a string."""
        assert isinstance(constants.__version__, str)

    def test_version_format(self) -> None:
        """Verify __version__ follows expected format."""
        version = constants.__version__
        assert version.startswith("0.0.0") or version[0].isdigit()

    def test_version_not_empty(self) -> None:
        """Verify __version__ is not empty."""
        assert len(constants.__version__) > 0


class TestConstantTypes:
    """Type validation tests for constants."""

    def test_env_prefix_is_str(self) -> None:
        """Verify ENV_PREFIX is a string."""
        assert isinstance(constants.ENV_PREFIX, str)

    def test_env_nested_delimiter_is_str(self) -> None:
        """Verify ENV_NESTED_DELIMITER is a string."""
        assert isinstance(constants.ENV_NESTED_DELIMITER, str)

    def test_max_feedback_text_length_is_positive(self) -> None:
        """Verify MAX_FEEDBACK_TEXT_LENGTH is positive."""
        assert constants.MAX_FEEDBACK_TEXT_LENGTH > 0

    def test_default_rating_min_positive(self) -> None:
        """Verify DEFAULT_RATING_MIN is positive."""
        assert constants.DEFAULT_RATING_MIN > 0

    def test_default_rating_max_greater_than_min(self) -> None:
        """Verify DEFAULT_RATING_MAX > DEFAULT_RATING_MIN."""
        assert constants.DEFAULT_RATING_MAX > constants.DEFAULT_RATING_MIN

    def test_max_context_size_is_positive(self) -> None:
        """Verify MAX_CONTEXT_SIZE is positive."""
        assert constants.MAX_CONTEXT_SIZE > 0


class TestConstantExports:
    """Verify all constants are exported in __all__."""

    def test_all_contains_expected(self) -> None:
        """Verify __all__ contains all expected constants."""
        expected = [
            "DEFAULT_RATING_MAX",
            "DEFAULT_RATING_MIN",
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
            "MAX_CONTEXT_SIZE",
            "MAX_FEEDBACK_TEXT_LENGTH",
            "__version__",
        ]
        for name in expected:
            assert name in constants.__all__