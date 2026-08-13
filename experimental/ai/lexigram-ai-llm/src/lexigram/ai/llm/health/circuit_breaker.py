"""Circuit breaker pattern for provider health management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class CircuitState(StrEnum):
    """Circuit breaker state enumeration."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, block requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for provider circuit breaker.

    Attributes:
        failure_threshold: Errors before opening circuit
        success_threshold: Successes before closing from half-open
        timeout_seconds: Time in open state before half-open
        window_size: Number of recent requests to track
    """

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 60
    window_size: int = 20


class ProviderCircuitBreaker:
    """Implements circuit breaker pattern for provider failures.

    Automatically stops requests to a provider after repeated failures,
    and gradually recovers when it becomes healthy again.
    """

    def __init__(
        self,
        provider_name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            provider_name: Provider identifier
            config: Circuit breaker configuration
        """
        self.provider_name = provider_name
        self.config = config or CircuitBreakerConfig()

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime | None = None
        self.opened_at: datetime | None = None
        self.request_times: list[datetime] = []

    async def record_success(self) -> None:
        """Record a successful request.

        May transition from HALF_OPEN → CLOSED.
        """
        now = datetime.now(UTC)
        self.request_times.append(now)

        # Prune old requests
        cutoff = now - timedelta(seconds=self.config.timeout_seconds)
        self.request_times = [t for t in self.request_times if t > cutoff]

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._close()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    async def record_failure(self, error: Exception) -> None:
        """Record a failed request.

        May transition CLOSED → OPEN.

        Args:
            error: Exception that occurred
        """
        now = datetime.now(UTC)
        self.last_failure_time = now
        self.failure_count += 1

        if self.failure_count >= self.config.failure_threshold:
            if self.state != CircuitState.OPEN:
                self._open(now)

        logger.warning(
            "provider_failure_recorded",
            provider=self.provider_name,
            failure_count=self.failure_count,
            circuit_state=self.state.value,
            error=str(error)[:100],
        )

    async def is_available(self) -> bool:
        """Check if provider is available for requests.

        Returns:
            False if circuit is OPEN, True otherwise
        """
        if self.state == CircuitState.OPEN:
            # Check if we should transition to HALF_OPEN
            if self.opened_at:
                elapsed = datetime.now(UTC) - self.opened_at
                if elapsed.total_seconds() >= self.config.timeout_seconds:
                    self._half_open()
                    return True  # Allow test request
            return False

        return True

    def _open(self, now: datetime) -> None:
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self.opened_at = now
        self.success_count = 0

        logger.error(
            "circuit_breaker_opened",
            provider=self.provider_name,
            failure_count=self.failure_count,
        )

    def _half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.failure_count = 0
        self.success_count = 0

        logger.info(
            "circuit_breaker_half_open",
            provider=self.provider_name,
        )

    def _close(self) -> None:
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None

        logger.info(
            "circuit_breaker_closed",
            provider=self.provider_name,
        )

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None
        self.request_times = []
