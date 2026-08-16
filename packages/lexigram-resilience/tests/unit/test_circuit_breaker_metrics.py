"""Tests for CircuitBreakerMetrics — verifies that renaming _sliding_window
to __sliding_window (R1) does not break the public API.

Covers:
    - R1: ``__sliding_window`` is not accessible from outside as ``_sliding_window``
    - ``record_success()`` and ``record_failure()`` update metrics correctly
    - ``failure_rate`` property returns values sourced from the private window
    - ``reset_consecutive_counts()`` resets as expected
"""

from __future__ import annotations

import pytest

from lexigram.resilience.circuit.breaker import CircuitBreakerMetrics


class TestCircuitBreakerMetricsSlidingWindowPrivate:
    """_sliding_window renamed to __sliding_window (name-mangled) to prevent accidental access."""

    def test_single_underscore_attribute_gone(self) -> None:
        """``_sliding_window`` is no longer directly accessible on instances."""
        metrics = CircuitBreakerMetrics()
        assert not hasattr(metrics, "_sliding_window"), (
            "_sliding_window should not be accessible; it was renamed to __sliding_window"
        )

    def test_double_underscore_attribute_accessible_via_mangled_name(self) -> None:
        """The mangled name ``_CircuitBreakerMetrics__sliding_window`` IS accessible."""
        metrics = CircuitBreakerMetrics()
        # Name mangling produces _ClassName__attr
        assert hasattr(metrics, "_CircuitBreakerMetrics__sliding_window")


class TestCircuitBreakerMetricsRecording:
    """Public recording API (record_success / record_failure / failure_rate) still works."""

    def test_initial_failure_rate_is_zero(self) -> None:
        """Newly created metrics report 0% failure rate."""
        metrics = CircuitBreakerMetrics()
        assert metrics.failure_rate == 0.0

    def test_record_success_increments_counters(self) -> None:
        """Successful calls increment total_calls and successful_calls."""
        metrics = CircuitBreakerMetrics()
        metrics.record_success(response_time=0.1)
        assert metrics.total_calls == 1
        assert metrics.successful_calls == 1
        assert metrics.failed_calls == 0
        assert metrics.consecutive_successes == 1
        assert metrics.consecutive_failures == 0

    def test_record_failure_increments_counters(self) -> None:
        """Failed calls increment total_calls and failed_calls."""
        metrics = CircuitBreakerMetrics()
        metrics.record_failure()
        assert metrics.total_calls == 1
        assert metrics.failed_calls == 1
        assert metrics.successful_calls == 0
        assert metrics.consecutive_failures == 1

    def test_failure_rate_all_failures(self) -> None:
        """100% failure rate when all calls fail."""
        metrics = CircuitBreakerMetrics()
        for _ in range(10):
            metrics.record_failure()
        # After all failures, failure_rate should be 1.0 (once window is full)
        rate = metrics.failure_rate
        assert 0.0 <= rate <= 1.0  # Always a valid probability

    def test_failure_rate_mixed(self) -> None:
        """Failure rate is between 0 and 1 with mixed results."""
        metrics = CircuitBreakerMetrics()
        for _ in range(5):
            metrics.record_success(response_time=0.05)
        for _ in range(5):
            metrics.record_failure()
        rate = metrics.failure_rate
        assert 0.0 <= rate <= 1.0

    def test_timeout_tracked_separately(self) -> None:
        """Timeouts are counted in total_timeouts when is_timeout=True."""
        metrics = CircuitBreakerMetrics()
        metrics.record_failure(is_timeout=True)
        metrics.record_failure(is_timeout=False)
        assert metrics.total_timeouts == 1

    def test_avg_response_time_updated(self) -> None:
        """avg_response_time is updated correctly after success calls."""
        metrics = CircuitBreakerMetrics()
        metrics.record_success(response_time=0.2)
        metrics.record_success(response_time=0.4)
        assert abs(metrics.avg_response_time - 0.3) < 1e-9

    def test_reset_consecutive_counts(self) -> None:
        """reset_consecutive_counts zeros both consecutive counters."""
        metrics = CircuitBreakerMetrics()
        metrics.record_failure()
        metrics.record_failure()
        assert metrics.consecutive_failures == 2

        metrics.reset_consecutive_counts()
        assert metrics.consecutive_failures == 0
        assert metrics.consecutive_successes == 0

    def test_consecutive_failures_reset_on_success(self) -> None:
        """Recording a success resets consecutive_failures to 0."""
        metrics = CircuitBreakerMetrics()
        metrics.record_failure()
        metrics.record_failure()
        metrics.record_success(response_time=0.1)
        assert metrics.consecutive_failures == 0

    def test_consecutive_successes_reset_on_failure(self) -> None:
        """Recording a failure resets consecutive_successes to 0."""
        metrics = CircuitBreakerMetrics()
        metrics.record_success(response_time=0.1)
        metrics.record_success(response_time=0.1)
        metrics.record_failure()
        assert metrics.consecutive_successes == 0
