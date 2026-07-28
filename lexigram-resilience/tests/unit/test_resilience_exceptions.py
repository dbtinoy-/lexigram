"""Unit tests for lexigram-resilience exceptions.

These tests verify the exception hierarchy and behavior in lexigram.resilience.exceptions.
"""

from lexigram.contracts.exceptions.resilience import (
    BulkheadError,
    CircuitBreakerError,
    ResilienceError,
    RetryError,
)
from lexigram.resilience.exceptions import (
    BulkheadRejectedError,
    CircuitOpenError,
    ResilienceTimeoutError,
    RetryExhaustedError,
)


class TestResilienceExceptionHierarchy:
    """Tests for resilience exception hierarchy."""

    def test_resilience_error_inherits_from_lexigram_error(self) -> None:
        from lexigram.contracts.exceptions import LexigramError

        assert issubclass(ResilienceError, LexigramError)

    def test_retry_error_inherits_from_resilience_error(self) -> None:
        assert issubclass(RetryError, ResilienceError)

    def test_circuit_breaker_error_inherits_from_resilience_error(self) -> None:
        assert issubclass(CircuitBreakerError, ResilienceError)

    def test_bulkhead_error_inherits_from_resilience_error(self) -> None:
        assert issubclass(BulkheadError, ResilienceError)


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError."""

    def test_retry_exhausted_error_inherits_from_retry_error(self) -> None:
        assert issubclass(RetryExhaustedError, RetryError)

    def test_retry_exhausted_error_default_message(self) -> None:
        error = RetryExhaustedError()
        assert error.message == "All retry attempts exhausted"

    def test_retry_exhausted_error_custom_message(self) -> None:
        error = RetryExhaustedError(message="Custom retry error")
        assert error.message == "Custom retry error"

    def test_retry_exhausted_error_with_attempts(self) -> None:
        error = RetryExhaustedError(attempts=5)
        assert error.attempts == 5
        assert error.details.get("attempts") == 5

    def test_retry_exhausted_error_with_last_error(self) -> None:
        original_error = ValueError("original error")
        error = RetryExhaustedError(last_error=original_error)
        assert "original error" in str(error.details.get("last_error", ""))

    def test_retry_exhausted_error_code(self) -> None:
        error = RetryExhaustedError()
        assert error._code == "LEX_ERR_RES_008"


class TestCircuitOpenError:
    """Tests for CircuitOpenError."""

    def test_circuit_open_error_inherits_from_circuit_breaker_error(self) -> None:
        assert issubclass(CircuitOpenError, CircuitBreakerError)

    def test_circuit_open_error_default_message(self) -> None:
        error = CircuitOpenError()
        assert error.message == "Circuit breaker is open"

    def test_circuit_open_error_custom_message(self) -> None:
        error = CircuitOpenError(message="Custom circuit open message")
        assert error.message == "Custom circuit open message"

    def test_circuit_open_error_code(self) -> None:
        error = CircuitOpenError()
        assert error._code == "LEX_ERR_RES_009"


class TestBulkheadRejectedError:
    """Tests for BulkheadRejectedError."""

    def test_bulkhead_rejected_error_inherits_from_bulkhead_error(self) -> None:
        assert issubclass(BulkheadRejectedError, BulkheadError)

    def test_bulkhead_rejected_error_default_message(self) -> None:
        error = BulkheadRejectedError()
        assert error.message == "Bulkhead capacity exceeded"

    def test_bulkhead_rejected_error_custom_message(self) -> None:
        error = BulkheadRejectedError(message="Custom bulkhead message")
        assert error.message == "Custom bulkhead message"

    def test_bulkhead_rejected_error_code(self) -> None:
        error = BulkheadRejectedError()
        assert error._code == "LEX_ERR_RES_010"


class TestResilienceTimeoutError:
    """Tests for ResilienceTimeoutError."""

    def test_resilience_timeout_error_inherits_from_resilience_error(self) -> None:
        assert issubclass(ResilienceTimeoutError, ResilienceError)

    def test_resilience_timeout_error_inherits_from_timeout_error(self) -> None:
        assert issubclass(ResilienceTimeoutError, TimeoutError)

    def test_resilience_timeout_error_isinstance_timeout(self) -> None:
        error = ResilienceTimeoutError()
        assert isinstance(error, TimeoutError)

    def test_resilience_timeout_error_default_message(self) -> None:
        error = ResilienceTimeoutError()
        assert error.message == "Operation timed out"

    def test_resilience_timeout_error_custom_message(self) -> None:
        error = ResilienceTimeoutError(message="Custom timeout")
        assert error.message == "Custom timeout"

    def test_resilience_timeout_error_code(self) -> None:
        error = ResilienceTimeoutError()
        assert error._code == "LEX_ERR_RES_011"


class TestExceptionAllExports:
    """Tests to verify __all__ exports."""

    def test_all_contains_all_exceptions(self) -> None:
        from lexigram.resilience import exceptions as exc_module

        expected = [
            "BulkheadError",
            "BulkheadRejectedError",
            "CircuitBreakerError",
            "CircuitOpenError",
            "ResilienceError",
            "ResilienceTimeoutError",
            "RetryError",
            "RetryExhaustedError",
        ]
        for item in expected:
            assert item in exc_module.__all__
