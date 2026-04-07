"""Unit tests for lexigram-resilience types.

These tests verify the type definitions and classes in lexigram.resilience.types.
"""

from typing import Any

import pytest

from lexigram.contracts.infra.resilience.enums import CircuitState as ContractsCircuitState
from lexigram.contracts.infra.resilience.models import CircuitBreakerConfig, RetryConfig, TimeoutConfig
from lexigram.resilience.config import BulkheadConfig
from lexigram.resilience.types import CircuitState, ResilienceStatus


class TestBulkheadConfig:
    """Tests for BulkheadConfig dataclass."""

    def test_bulkhead_config_defaults(self) -> None:
        config = BulkheadConfig()
        assert config.max_concurrent == 10
        assert config.queue_size == 100
        assert config.timeout == 30.0
        assert config.name == ""

    def test_bulkhead_config_custom_values(self) -> None:
        config = BulkheadConfig(
            max_concurrent=20,
            queue_size=200,
            timeout=60.0,
            name="test_bulkhead",
        )
        assert config.max_concurrent == 20
        assert config.queue_size == 200
        assert config.timeout == 60.0
        assert config.name == "test_bulkhead"

class TestResilienceStatus:
    """Tests for ResilienceStatus enum."""

    def test_resilience_status_pending_value(self) -> None:
        assert ResilienceStatus.PENDING.value == "pending"

    def test_resilience_status_active_value(self) -> None:
        assert ResilienceStatus.ACTIVE.value == "active"

    def test_resilience_status_completed_value(self) -> None:
        assert ResilienceStatus.COMPLETED.value == "completed"

    def test_resilience_status_is_str_enum(self) -> None:
        assert isinstance(ResilienceStatus.PENDING, str)


class TestCircuitState:
    """Tests for CircuitState enum (from contracts)."""

    def test_circuit_state_closed_value(self) -> None:
        assert CircuitState.CLOSED.value == "closed"

    def test_circuit_state_open_value(self) -> None:
        assert CircuitState.OPEN.value == "open"

    def test_circuit_state_half_open_value(self) -> None:
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_circuit_state_is_str_enum(self) -> None:
        assert isinstance(CircuitState.CLOSED, str)

    def test_circuit_state_from_contracts(self) -> None:
        # Verify it's the same as the one from contracts
        assert CircuitState is ContractsCircuitState


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_retry_config_defaults(self) -> None:
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True
        assert config.retry_on == (Exception,)
        assert config.retry_if is None
        assert config.on_retry is None
        assert config.retry_on_result is None
        assert config.abort_on == ()
        assert config.abort_if is None
        assert config.retry_sync is False

    def test_retry_config_custom_values(self) -> None:
        def custom_retry_fn(exc: Exception) -> bool:
            return True

        def abort_fn(result: Any) -> bool:
            return result is None

        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            backoff_factor=3.0,
            jitter=False,
            retry_on=(ValueError, TypeError),
            retry_if=custom_retry_fn,
            abort_on=(KeyError,),
            abort_if=abort_fn,
            retry_sync=True,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.backoff_factor == 3.0
        assert config.jitter is False
        assert config.retry_on == (ValueError, TypeError)
        assert config.retry_if is custom_retry_fn
        assert config.abort_on == (KeyError,)
        assert config.abort_if is abort_fn
        assert config.retry_sync is True

    def test_retry_config_is_frozen(self) -> None:
        config = RetryConfig()
        with pytest.raises(AttributeError):
            config.max_attempts = 10


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig dataclass."""

    def test_circuit_breaker_config_defaults(self) -> None:
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.expected_exception == (Exception,)
        assert config.success_threshold == 3
        assert config.timeout == 30.0
        assert config.name == ""
        assert config.sliding_window_seconds == 60.0
        assert config.failure_rate_threshold == 0.5
        assert config.backend == "memory"

    def test_circuit_breaker_config_custom_values(self) -> None:
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=120.0,
            expected_exception=(ValueError, TypeError),
            success_threshold=5,
            timeout=60.0,
            name="test_breaker",
            sliding_window_seconds=120.0,
            failure_rate_threshold=0.3,
            backend="redis",
        )
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 120.0
        assert config.expected_exception == (ValueError, TypeError)
        assert config.success_threshold == 5
        assert config.timeout == 60.0
        assert config.name == "test_breaker"
        assert config.sliding_window_seconds == 120.0
        assert config.failure_rate_threshold == 0.3
        assert config.backend == "redis"

    def test_circuit_breaker_config_backend_values(self) -> None:
        config_memory = CircuitBreakerConfig(backend="memory")
        assert config_memory.backend == "memory"

        config_redis = CircuitBreakerConfig(backend="redis")
        assert config_redis.backend == "redis"

        config_consul = CircuitBreakerConfig(backend="consul")
        assert config_consul.backend == "consul"

    def test_circuit_breaker_config_is_frozen(self) -> None:
        config = CircuitBreakerConfig()
        with pytest.raises(AttributeError):
            config.failure_threshold = 10


class TestTimeoutConfig:
    """Tests for TimeoutConfig dataclass."""

    def test_timeout_config_defaults(self) -> None:
        config = TimeoutConfig()
        assert config.timeout == 30.0
        assert config.timeout_message == "Operation timed out"

    def test_timeout_config_custom_values(self) -> None:
        config = TimeoutConfig(
            timeout=60.0,
            timeout_message="Custom timeout message",
        )
        assert config.timeout == 60.0
        assert config.timeout_message == "Custom timeout message"

    def test_timeout_config_is_frozen(self) -> None:
        config = TimeoutConfig()
        with pytest.raises(AttributeError):
            config.timeout = 10.0


class TestAllExports:
    """Tests to verify __all__ exports."""

    def test_all_contains_expected_types(self) -> None:
        from lexigram.resilience import types as type_module

        expected = [
            "BulkheadConfig",
            "CircuitBreakerConfig",
            "CircuitState",
            "ResilienceStatus",
            "RetryConfig",
            "TimeoutConfig",
        ]
        for item in expected:
            assert item in type_module.__all__
