"""Tests for AI workers exceptions."""

from __future__ import annotations

import pytest

from lexigram.ai.workers.exceptions import DLQError, MaintenanceError, WorkerError
from lexigram.contracts.ai.exceptions import AIError


class TestWorkerError:
    """Test WorkerError base exception."""

    def test_inherits_from_ai_error(self) -> None:
        """Test WorkerError inherits from AIError."""
        assert issubclass(WorkerError, AIError)

    def test_has_error_code(self) -> None:
        """Test WorkerError has an error code."""
        error = WorkerError("test message")
        assert error._code == "LEX_ERR_AIWORK_001"

    def test_can_be_raised(self) -> None:
        """Test WorkerError can be raised and caught."""
        with pytest.raises(WorkerError) as exc_info:
            raise WorkerError("test error")
        assert "test error" in str(exc_info.value)


class TestDLQError:
    """Test DLQError exception."""

    def test_inherits_from_worker_error(self) -> None:
        """Test DLQError inherits from WorkerError."""
        assert issubclass(DLQError, WorkerError)

    def test_has_error_code(self) -> None:
        """Test DLQError has an error code."""
        error = DLQError("dlq error")
        assert error._code == "LEX_ERR_AIWORK_002"

    def test_can_be_raised(self) -> None:
        """Test DLQError can be raised and caught."""
        with pytest.raises(DLQError) as exc_info:
            raise DLQError(" DLQ failed")
        assert "DLQ failed" in str(exc_info.value)


class TestMaintenanceError:
    """Test MaintenanceError exception."""

    def test_inherits_from_worker_error(self) -> None:
        """Test MaintenanceError inherits from WorkerError."""
        assert issubclass(MaintenanceError, WorkerError)

    def test_has_error_code(self) -> None:
        """Test MaintenanceError has an error code."""
        error = MaintenanceError("maintenance error")
        assert error._code == "LEX_ERR_AIWORK_003"

    def test_can_be_raised(self) -> None:
        """Test MaintenanceError can be raised and caught."""
        with pytest.raises(MaintenanceError) as exc_info:
            raise MaintenanceError("maintenance failed")
        assert "maintenance failed" in str(exc_info.value)


class TestExceptionHierarchy:
    """Test exception hierarchy."""

    def test_worker_error_is_ai_error(self) -> None:
        """Test catching WorkerError catches AI errors."""
        with pytest.raises(AIError):
            raise WorkerError("test")

    def test_dlq_error_is_worker_error(self) -> None:
        """Test catching WorkerError catches DLQError."""
        with pytest.raises(WorkerError):
            raise DLQError("test")

    def test_maintenance_error_is_worker_error(self) -> None:
        """Test catching WorkerError catches MaintenanceError."""
        with pytest.raises(WorkerError):
            raise MaintenanceError("test")

    def test_can_catch_specific_exception(self) -> None:
        """Test specific exceptions can be caught independently."""
        with pytest.raises(DLQError):
            raise DLQError("specific")
        with pytest.raises(MaintenanceError):
            raise MaintenanceError("specific")


class TestExceptionExports:
    """Test exceptions are properly exported."""

    def test_all_exports(self) -> None:
        """Test __all__ contains expected exceptions."""
        from lexigram.ai.workers import exceptions

        expected = ["DLQError", "MaintenanceError", "WorkerError"]
        assert sorted(exceptions.__all__) == sorted(expected)