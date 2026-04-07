"""Tests for prompt exceptions module."""

from __future__ import annotations

import pytest
from lexigram.ai.prompt.exceptions import (
    PromptError,
    PromptRenderError,
    PromptValidationError,
    PromptNotFoundError,
    PromptVersionError,
    PromptConfigError,
    OptimizationError,
)


class TestExceptionInheritance:
    """Tests for exception hierarchy."""

    def test_prompt_error_inherits_exception(self) -> None:
        assert issubclass(PromptError, Exception)

    def test_prompt_render_error_inherits_prompt_error(self) -> None:
        assert issubclass(PromptRenderError, PromptError)

    def test_prompt_validation_error_inherits_prompt_error(self) -> None:
        assert issubclass(PromptValidationError, PromptError)

    def test_prompt_not_found_error_inherits_prompt_error(self) -> None:
        assert issubclass(PromptNotFoundError, PromptError)

    def test_prompt_version_error_inherits_prompt_error(self) -> None:
        assert issubclass(PromptVersionError, PromptError)

    def test_prompt_config_error_inherits_prompt_error(self) -> None:
        assert issubclass(PromptConfigError, PromptError)

    def test_optimization_error_inherits_prompt_error(self) -> None:
        assert issubclass(OptimizationError, PromptError)

    def test_all_leaf_exceptions_inherit_base(self) -> None:
        leaf_exceptions = [
            PromptRenderError,
            PromptValidationError,
            PromptNotFoundError,
            PromptVersionError,
            PromptConfigError,
            OptimizationError,
        ]
        for exc in leaf_exceptions:
            assert issubclass(exc, PromptError)


class TestPromptError:
    """Tests for base PromptError class."""

    def test_can_raise_without_message(self) -> None:
        with pytest.raises(PromptError):
            raise PromptError()

    def test_can_raise_with_message(self) -> None:
        with pytest.raises(PromptError, match="test message"):
            raise PromptError("test message")

    def test_can_catch_as_base(self) -> None:
        with pytest.raises(PromptError):
            raise PromptRenderError("render failed")

    def test_message_accessible(self) -> None:
        err = PromptError("custom message")
        assert err.message == "custom message"
        assert "custom message" in str(err)


class TestPromptRenderError:
    """Tests for PromptRenderError."""

    def test_can_raise_with_message(self) -> None:
        with pytest.raises(PromptRenderError, match="missing variable"):
            raise PromptRenderError("missing variable")

    def test_raised_on_missing_variable(self) -> None:
        with pytest.raises(PromptRenderError, match="Missing variable"):
            raise PromptRenderError("Missing variable 'x' in template.")


class TestPromptValidationError:
    """Tests for PromptValidationError."""

    def test_can_raise_with_message(self) -> None:
        with pytest.raises(PromptValidationError, match="type mismatch"):
            raise PromptValidationError("type mismatch")


class TestPromptNotFoundError:
    """Tests for PromptNotFoundError."""

    def test_can_raise_with_message(self) -> None:
        with pytest.raises(PromptNotFoundError, match="template not found"):
            raise PromptNotFoundError("template not found")


class TestPromptVersionError:
    """Tests for PromptVersionError."""

    def test_can_raise_with_message(self) -> None:
        with pytest.raises(PromptVersionError, match="invalid version"):
            raise PromptVersionError("invalid version")


class TestPromptConfigError:
    """Tests for PromptConfigError."""

    def test_can_raise_with_message(self) -> None:
        with pytest.raises(PromptConfigError, match="invalid config"):
            raise PromptConfigError("invalid config")


class TestOptimizationError:
    """Tests for OptimizationError."""

    def test_can_raise_with_message(self) -> None:
        with pytest.raises(OptimizationError, match="optimization failed"):
            raise OptimizationError("optimization failed")


class TestChainedExceptions:
    """Tests for exception chaining."""

    def test_render_error_can_chain(self) -> None:
        try:
            cause = ValueError("original error")
            raise PromptRenderError("render failed") from cause
        except PromptRenderError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)

    def test_validation_error_can_chain(self) -> None:
        try:
            cause = TypeError("original error")
            raise PromptValidationError("validation failed") from cause
        except PromptValidationError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, TypeError)


class TestAllExports:
    """Verify all expected exceptions are exported."""

    def test_all_in_all_list(self) -> None:
        expected = [
            "OptimizationError",
            "PromptConfigError",
            "PromptError",
            "PromptNotFoundError",
            "PromptRenderError",
            "PromptValidationError",
            "PromptVersionError",
        ]
        from lexigram.ai.prompt import exceptions
        assert set(expected) == set(exceptions.__all__)