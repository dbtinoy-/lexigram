"""Sliding window counter and metrics for the circuit breaker."""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock

logger = get_logger(__name__)


class BucketedSlidingWindowCounter:
    """High-performance O(1) bucketed sliding window counter.

    Uses a fixed-size ring buffer divided into time buckets for O(1)
    recording and failure rate calculation. Much more efficient under
    high load (1000+ req/sec) than the list-based implementation.

    Design:
    - Divide the window into N buckets (e.g., 60 x 1-second buckets)
    - Each bucket tracks successes and failures for that second
    - Rotating the bucket is O(1) - just reset the counters
    - Total failure rate = sum(all_buckets) / total_calls
    """

    def __init__(
        self,
        window_seconds: float = 60.0,
        bucket_size: float = 1.0,
    ) -> None:
        self._window = window_seconds
        self._bucket_size = bucket_size
        self._num_buckets = max(1, int(window_seconds / bucket_size))

        # Ring buffer of buckets
        self._buckets: list[dict[str, int | float]] = [
            {"success": 0, "failure": 0, "timestamp": 0.0}
            for _ in range(self._num_buckets)
        ]
        self._current_bucket = 0
        self._last_update = ambient_clock.monotonic()
        self._total_success = 0
        self._total_failure = 0

    def _rotate_if_needed(self) -> None:
        """Rotate buckets if time has advanced. O(1) operation."""
        now = ambient_clock.monotonic()

        # Calculate how many buckets to skip
        elapsed = now - self._last_update
        if elapsed < self._bucket_size:
            return

        buckets_to_skip = int(elapsed / self._bucket_size)
        if buckets_to_skip >= self._num_buckets:
            # Window expired - reset everything
            for bucket in self._buckets:
                bucket["success"] = 0
                bucket["failure"] = 0
            self._total_success = 0
            self._total_failure = 0
        else:
            # Rotate through the buckets we missed
            for _ in range(buckets_to_skip):
                self._current_bucket = (self._current_bucket + 1) % self._num_buckets
                bucket = self._buckets[self._current_bucket]
                # Subtract the old bucket's counts from totals
                self._total_success -= bucket["success"]  # type: ignore[assignment]
                self._total_failure -= bucket["failure"]  # type: ignore[assignment]
                # Reset the bucket
                bucket["success"] = 0
                bucket["failure"] = 0
                bucket["timestamp"] = now

        self._last_update = now

    def record_success(self) -> None:
        """Record a successful call. O(1) operation."""
        self._rotate_if_needed()
        bucket = self._buckets[self._current_bucket]
        bucket["success"] += 1
        self._total_success += 1

    def record_failure(self) -> None:
        """Record a failed call. O(1) operation."""
        self._rotate_if_needed()
        bucket = self._buckets[self._current_bucket]
        bucket["failure"] += 1
        self._total_failure += 1

    def failure_rate(self) -> float:
        """Calculate failure rate in the current window. O(1) operation."""
        self._rotate_if_needed()
        total = self._total_success + self._total_failure
        if total == 0:
            return 0.0
        return self._total_failure / total

    def total_calls(self) -> int:
        """Total calls in the window. O(1) operation."""
        self._rotate_if_needed()
        return self._total_success + self._total_failure


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring with behavioral logic."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    state_changes: int = 0
    last_state_change: float | None = None
    total_timeouts: int = 0
    avg_response_time: float = 0.0

    # Internal sliding window for rate-based logic (double-underscore: class-private)
    __sliding_window: BucketedSlidingWindowCounter = field(
        default_factory=BucketedSlidingWindowCounter,
        init=False,
        repr=False,
    )

    def record_success(self, response_time: float) -> None:
        """Record a successful call and update internal state."""
        self.total_calls += 1
        self.successful_calls += 1
        self.consecutive_failures = 0
        self.consecutive_successes += 1
        self.last_success_time = ambient_clock.monotonic()

        # Update rolling average
        if self.total_calls == 1:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (
                (self.avg_response_time * (self.total_calls - 1)) + response_time
            ) / self.total_calls

        self.__sliding_window.record_success()

    def record_failure(self, is_timeout: bool = False) -> None:
        """Record a failed call and update internal state."""
        self.total_calls += 1
        self.failed_calls += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_time = ambient_clock.monotonic()

        if is_timeout:
            self.total_timeouts += 1

        self.__sliding_window.record_failure()

    @property
    def failure_rate(self) -> float:
        """Current failure rate from the sliding window."""
        return self.__sliding_window.failure_rate()

    def reset_consecutive_counts(self) -> None:
        """Reset consecutive counters (usually on state change)."""
        self.consecutive_failures = 0
        self.consecutive_successes = 0
