"""Tests for skill exceptions."""

from __future__ import annotations

import pytest

from lexigram.ai.skills.exceptions import (
    SkillNotFoundError,
    SkillAlreadyRegisteredError,
    SkillValidationError,
    SkillPermissionDeniedError,
    SkillTimeoutError,
    SkillRoutingError,
    SkillExecutionError,
)


class TestSkillNotFoundError:
    """Test SkillNotFoundError."""

    def test_error_creation(self) -> None:
        """SkillNotFoundError should be creatable with skill name."""
        error = SkillNotFoundError("my_skill")

        assert "my_skill" in str(error)
        assert "not found" in str(error).lower()

    def test_error_includes_skill_name(self) -> None:
        """Error should store skill name."""
        error = SkillNotFoundError("math_skill")

        assert hasattr(error, "skill_name")


class TestSkillAlreadyRegisteredError:
    """Test SkillAlreadyRegisteredError."""

    def test_error_creation(self) -> None:
        """SkillAlreadyRegisteredError should be creatable."""
        error = SkillAlreadyRegisteredError("duplicate_skill")

        assert "duplicate_skill" in str(error)

    def test_error_message(self) -> None:
        """Error should indicate skill is already registered."""
        error = SkillAlreadyRegisteredError("my_skill")

        assert "already registered" in str(error).lower()


class TestSkillValidationError:
    """Test SkillValidationError."""

    def test_error_with_single_error(self) -> None:
        """SkillValidationError should accept list of errors."""
        errors = ["Parameter 'x' is required"]
        error = SkillValidationError("calc_skill", errors)

        assert "calc_skill" in str(error)
        assert "Parameter" in str(error)

    def test_error_with_multiple_errors(self) -> None:
        """SkillValidationError should handle multiple errors."""
        errors = [
            "Parameter 'x' must be numeric",
            "Parameter 'y' cannot be negative",
        ]
        error = SkillValidationError("math_skill", errors)

        assert len(error.errors) == 2
        assert all(e in str(error) for e in errors)

    def test_error_stores_errors_list(self) -> None:
        """Error should store the errors list."""
        errors = ["error1", "error2"]
        error = SkillValidationError("skill", errors)

        assert error.errors == errors


class TestSkillPermissionDeniedError:
    """Test SkillPermissionDeniedError."""

    def test_error_creation(self) -> None:
        """SkillPermissionDeniedError should indicate required permissions."""
        error = SkillPermissionDeniedError("admin_skill", ["admin", "write"])

        assert "admin_skill" in str(error)
        assert "admin" in str(error)

    def test_error_stores_required_permissions(self) -> None:
        """Error should store required permissions."""
        required = ["admin", "user_mgmt"]
        error = SkillPermissionDeniedError("user_skill", required)

        assert error.required == required

    def test_permission_denied_message(self) -> None:
        """Error should indicate permission denial."""
        error = SkillPermissionDeniedError("restricted", ["admin"])

        assert "permission denied" in str(error).lower()


class TestSkillTimeoutError:
    """Test SkillTimeoutError."""

    def test_error_creation(self) -> None:
        """SkillTimeoutError should capture timeout info."""
        error = SkillTimeoutError("long_running_skill", 30.0)

        assert "long_running_skill" in str(error)
        assert "30" in str(error)

    def test_error_stores_timeout(self) -> None:
        """Error should store timeout value."""
        error = SkillTimeoutError("skill", 60.5)

        assert error.timeout_seconds == 60.5

    def test_timeout_in_message(self) -> None:
        """Error message should mention timeout."""
        error = SkillTimeoutError("skill", 10.0)

        assert "timed out" in str(error).lower()


class TestSkillRoutingError:
    """Test SkillRoutingError."""

    def test_error_creation(self) -> None:
        """SkillRoutingError should be creatable."""
        error = SkillRoutingError("No matching route for request")

        assert "No matching route" in str(error)

    def test_default_message(self) -> None:
        """SkillRoutingError should have default message."""
        error = SkillRoutingError()

        assert len(str(error)) > 0


class TestSkillExecutionError:
    """Test SkillExecutionError."""

    def test_error_creation(self) -> None:
        """SkillExecutionError should be creatable with message."""
        error = SkillExecutionError("Execution failed after retries")

        assert "Execution failed" in str(error)

    def test_error_with_cause(self) -> None:
        """SkillExecutionError should support cause."""
        cause = RuntimeError("Underlying error")
        error = SkillExecutionError("Failed to execute", cause=cause)

        assert error.cause is cause

    def test_error_with_skill_name(self) -> None:
        """SkillExecutionError should accept skill name."""
        error = SkillExecutionError("Failed", skill_name="my_skill")

        assert hasattr(error, "skill_name")

    def test_execution_error_chaining(self) -> None:
        """SkillExecutionError should support exception chaining."""
        try:
            raise ValueError("Original")
        except ValueError as e:
            error = SkillExecutionError("Wrapped", cause=e)

            assert error.cause is not None
            assert isinstance(error.cause, ValueError)
