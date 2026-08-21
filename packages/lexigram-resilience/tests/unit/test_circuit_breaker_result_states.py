"""Circuit-breaker state transitions and metrics tests."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.contracts.infra.resilience import CircuitState
from lexigram.contracts.infra.resilience.models import CircuitBreakerConfig
from lexigram.resilience.circuit.breaker import CircuitBreaker
from lexigram.resilience.exceptions import CircuitOpenError



class ServiceError(Exception):
    """Simulates a service error."""

    pass




class TestCircuitBreakerStateTransitions:
    """Tests for circuit breaker state transitions."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_starts_closed(self) -> None:
        """Test that circuit breaker starts in CLOSED state."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config=config)

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_transitions_closed_to_open(self) -> None:
        """Test state transition from CLOSED to OPEN on failure threshold."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=2,
            recovery_timeout=1.0,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        async def failing_operation() -> str:
            raise ServiceError("Service failed")

        # First failure
        with pytest.raises(ServiceError):
            await breaker.execute(failing_operation)

        assert breaker.state == CircuitState.CLOSED

        # Second failure - should trigger state change to OPEN
        with pytest.raises(ServiceError):
            await breaker.execute(failing_operation)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_rejects_calls(self) -> None:
        """Test that OPEN circuit rejects further calls without invoking."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=1.0,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        call_count = 0

        async def operation() -> str:
            nonlocal call_count
            call_count += 1
            raise ServiceError("Service failed")

        # Trigger circuit open
        with pytest.raises(ServiceError):
            await breaker.execute(operation)

        assert breaker.state == CircuitState.OPEN

        # Circuit should be open, rejecting the call
        with pytest.raises(CircuitOpenError):
            await breaker.execute(operation)

        # Verify the operation was not called a second time
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_to_half_open_transition(self) -> None:
        """Test state transition from OPEN to HALF_OPEN after recovery timeout."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=0.1,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        call_count = 0

        async def failing_operation() -> str:
            raise ServiceError("Service failed")

        async def working_operation() -> str:
            return "success"

        # Trigger circuit open
        with pytest.raises(ServiceError):
            await breaker.execute(failing_operation)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # After timeout, first call should transition to HALF_OPEN and attempt call
        result = await breaker.execute(working_operation)

        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_to_closed_on_success(self) -> None:
        """Test state transition from HALF_OPEN to CLOSED on success threshold."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2,  # Need 2 successes to close from HALF_OPEN
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        async def failing_operation() -> str:
            raise ServiceError("Service failed")

        async def working_operation() -> str:
            return "success"

        # Trigger circuit open
        with pytest.raises(ServiceError):
            await breaker.execute(failing_operation)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Transition to HALF_OPEN and succeed
        result = await breaker.execute(working_operation)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

        # One more success to reach threshold and close
        result = await breaker.execute(working_operation)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_to_open_on_failure(self) -> None:
        """Test state transition from HALF_OPEN back to OPEN on failure."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        async def failing_operation() -> str:
            raise ServiceError("Service failed")

        async def working_operation() -> str:
            return "success"

        # Trigger circuit open
        with pytest.raises(ServiceError):
            await breaker.execute(failing_operation)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Transition to HALF_OPEN with success
        result = await breaker.execute(working_operation)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

        # Now fail - should go back to OPEN
        with pytest.raises(ServiceError):
            await breaker.execute(failing_operation)

        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerMetrics:
    """Tests for circuit breaker metrics collection."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_tracks_successes(self) -> None:
        """Test that circuit breaker tracks successful calls."""
        config = CircuitBreakerConfig(name="test")
        breaker = CircuitBreaker(config=config)

        async def success() -> str:
            return "ok"

        result = await breaker.execute(success)

        assert result == "ok"
        metrics = breaker.get_metrics()
        assert metrics["success_count"] == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_tracks_failures(self) -> None:
        """Test that circuit breaker tracks failed calls."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=3,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        async def failure() -> str:
            raise ServiceError("fail")

        with pytest.raises(ServiceError):
            await breaker.execute(failure)

        metrics = breaker.get_metrics()
        assert metrics["failure_count"] == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_state_changes(self) -> None:
        """Test that circuit breaker tracks state changes."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=1.0,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        async def failure() -> str:
            raise ServiceError("fail")

        # Trigger state change CLOSED -> OPEN
        with pytest.raises(ServiceError):
            await breaker.execute(failure)

        metrics = breaker.get_metrics()
        assert metrics["state"] == CircuitState.OPEN.value


