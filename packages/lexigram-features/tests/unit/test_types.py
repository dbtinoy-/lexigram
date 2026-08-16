"""Tests for feature flags types."""

import pytest

from lexigram.features.types import Flag, FlagContext, FlagEvaluation, FlagType


class TestFlagType:
    """Tests for FlagType enum."""

    def test_has_boolean_type(self) -> None:
        """Should have BOOLEAN type."""
        assert FlagType.BOOLEAN is not None


class TestFlag:
    """Tests for Flag dataclass."""

    def test_create_boolean_flag(self) -> None:
        """Should create a boolean flag."""
        flag = Flag(
            name="dark-mode",
            type=FlagType.BOOLEAN,
            enabled=True,
        )
        assert flag.name == "dark-mode"
        assert flag.type == FlagType.BOOLEAN
        assert flag.enabled is True


class TestFlagContext:
    """Tests for FlagContext dataclass."""

    def test_create_empty_context(self) -> None:
        """Should create an empty context."""
        ctx = FlagContext()
        # Check that user_id is None by default
        assert ctx.user_id is None


class TestFlagEvaluation:
    """Tests for FlagEvaluation dataclass."""

    def test_create_evaluation(self) -> None:
        """Should create a flag evaluation result."""
        eval_result = FlagEvaluation(
            flag_name="dark-mode",
            enabled=True,
            reason="default",
        )
        assert eval_result.flag_name == "dark-mode"
        assert eval_result.enabled is True
