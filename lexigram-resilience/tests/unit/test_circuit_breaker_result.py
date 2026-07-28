"""Tests for circuit breaker with Result[T, E] integration.

This test suite verifies that circuit breaker operations properly integrate
with the Result pattern, managing state transitions and returning Result
types for operations that can fail.
"""

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


class TestCircuitBreakerWithFallback:
    """Tests for circuit breaker with fallback."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_executes_fallback_when_open(self) -> None:
        """Test that fallback is executed when circuit is open."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=1.0,
            expected_exception=(ServiceError,),
        )

        async def fallback() -> str:
            return "fallback"

        breaker = CircuitBreaker(config=config, fallback=fallback)

        async def failure() -> str:
            raise ServiceError("fail")

        # Trigger circuit open
        with pytest.raises(ServiceError):
            await breaker.execute(failure)

        assert breaker.state == CircuitState.OPEN

        # Now the circuit is open, fallback should be called
        result = await breaker.execute(failure)
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_circuit_breaker_no_fallback_raises_circuit_open_error(
        self,
    ) -> None:
        """Test that CircuitOpenError is raised when no fallback defined."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=1.0,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        async def failure() -> str:
            raise ServiceError("fail")

        # Trigger circuit open
        with pytest.raises(ServiceError):
            await breaker.execute(failure)

        assert breaker.state == CircuitState.OPEN

        # Now the circuit is open, should raise CircuitOpenError
        with pytest.raises(CircuitOpenError):
            await breaker.execute(failure)

    @pytest.mark.asyncio
    async def test_circuit_breaker_fallback_receives_arguments(self) -> None:
        """Test that fallback receives the same arguments as the main function."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=1.0,
            expected_exception=(ServiceError,),
        )

        async def fallback(x: int) -> int:
            return x * 2

        breaker = CircuitBreaker(config=config, fallback=fallback)

        async def failure(x: int) -> int:
            raise ServiceError("fail")

        # Trigger circuit open
        with pytest.raises(ServiceError):
            await breaker.execute(failure, 5)

        assert breaker.state == CircuitState.OPEN

        # Fallback should receive the argument
        result = await breaker.execute(failure, 5)
        assert result == 10


class TestCircuitBreakerDecorator:
    """Tests for circuit breaker as a decorator."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator_on_async_function(self) -> None:
        """Test circuit breaker decorator on async function."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=1.0,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        call_count = 0

        @breaker
        async def operation() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ServiceError("fail")
            return "success"

        # First call fails and triggers circuit open
        with pytest.raises(ServiceError):
            await operation()

        assert breaker.state == CircuitState.OPEN

        # Second call is rejected by open circuit
        with pytest.raises(CircuitOpenError):
            await operation()

        # Operation should not have been called
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator_on_sync_function(self) -> None:
        """Test circuit breaker decorator on sync function (runs in executor)."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=1.0,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        call_count = 0

        @breaker
        def sync_operation() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ServiceError("fail")
            return "success"

        # First call fails and triggers circuit open
        with pytest.raises(ServiceError):
            await sync_operation()

        assert breaker.state == CircuitState.OPEN

        # Second call is rejected by open circuit
        with pytest.raises(CircuitOpenError):
            await sync_operation()

        # Operation should not have been called
        assert call_count == 1


class TestCircuitBreakerContextManager:
    """Tests for circuit breaker as context manager."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_protect_success(self) -> None:
        """Test circuit breaker protect context manager with success."""
        config = CircuitBreakerConfig(name="test")
        breaker = CircuitBreaker(config=config)

        async with breaker.protect():
            result = "success"

        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_protect_failure(self) -> None:
        """Test circuit breaker protect context manager with failure."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=1.0,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        with pytest.raises(ServiceError):
            async with breaker.protect():
                raise ServiceError("fail")

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_protect_prevents_calls_when_open(self) -> None:
        """Test that protect raises CircuitOpenError when circuit is open."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=1.0,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        # Open the circuit
        with pytest.raises(ServiceError):
            async with breaker.protect():
                raise ServiceError("fail")

        assert breaker.state == CircuitState.OPEN

        # Try to protect when open
        with pytest.raises(CircuitOpenError):
            async with breaker.protect():
                pass


class TestCircuitBreakerPresets:
    """Tests for circuit breaker preset configurations."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_sensitive_preset(self) -> None:
        """Test sensitive preset for critical dependencies."""
        breaker = CircuitBreaker.sensitive()

        assert breaker.config.failure_threshold == 3
        assert breaker.config.recovery_timeout == 30.0
        assert breaker.config.success_threshold == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_tolerant_preset(self) -> None:
        """Test tolerant preset for non-critical dependencies."""
        breaker = CircuitBreaker.tolerant()

        assert breaker.config.failure_threshold == 10
        assert breaker.config.recovery_timeout == 120.0
        assert breaker.config.success_threshold == 5


class TestCircuitBreakerManualControl:
    """Tests for manual circuit breaker control."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_manual_reset(self) -> None:
        """Test manual reset of circuit breaker."""
        config = CircuitBreakerConfig(
            name="test",
            failure_threshold=1,
            recovery_timeout=1.0,
            expected_exception=(ServiceError,),
        )
        breaker = CircuitBreaker(config=config)

        # Open the circuit
        with pytest.raises(ServiceError):
            async with breaker.protect():
                raise ServiceError("fail")

        assert breaker.state == CircuitState.OPEN

        # Manually reset
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_force_open(self) -> None:
        """Test force opening the circuit."""
        config = CircuitBreakerConfig(name="test")
        breaker = CircuitBreaker(config=config)

        assert breaker.state == CircuitState.CLOSED

        # Force open
        breaker.force_open()

        assert breaker.state == CircuitState.OPEN


class TestConcurrencyBugFixes:
    """Regression tests for P0 concurrency bugs."""

    @pytest.mark.asyncio
    async def test_run_in_executor_passes_kwargs_to_sync_func(self) -> None:
        """P0-1: sync functions called via run_in_executor must receive their kwargs."""
        config = CircuitBreakerConfig(name="test-kwargs", failure_threshold=5, timeout=5.0)
        cb = CircuitBreaker(config=config)

        def sync_fn(*, multiplier: int) -> int:
            return 42 * multiplier

        result = await cb.execute(sync_fn, multiplier=2)
        assert result == 84

    @pytest.mark.asyncio
    async def test_protect_does_not_corrupt_failure_state_when_circuit_opened_while_yielded(
        self,
    ) -> None:
        """P0-2: protect() must not reset consecutive_failures when the circuit is
        opened by a concurrent coroutine while the context manager is yielded.

        Setup:
          1. Drive the circuit to 3 consecutive failures (below the threshold of 5,
             so the circuit remains CLOSED).
          2. Enter protect() — the circuit is CLOSED so we pass the guard.
          3. While inside the context (i.e. between lock-release and yield-resume),
             force-open the circuit to simulate a concurrent coroutine that records
             enough additional failures to open it.
          4. Let protect() exit cleanly (no exception raised inside).

        Expected (with fix):  consecutive_failures is unchanged (still 3) because
                              _record_success must be skipped on an OPEN circuit.
        Actual (without fix): _record_success resets consecutive_failures to 0,
                              corrupting the failure-count state machine.
        """
        config = CircuitBreakerConfig(
            name="test-p02-race",
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=(ServiceError,),
        )
        cb = CircuitBreaker(config=config)

        # Drive 3 failures — circuit stays CLOSED (threshold is 5)
        for _ in range(3):
            with pytest.raises(ServiceError):
                await cb.execute(_raise_service_error)

        assert cb.state == CircuitState.CLOSED
        assert cb.get_metrics()["consecutive_failures"] == 3

        # Coordinate the race: pause inside the context manager body
        inside_event = asyncio.Event()
        resume_event = asyncio.Event()

        async def protected_task() -> None:
            async with cb.protect():
                # Signal: we are now past the lock, between yield and success-recording
                inside_event.set()
                # Park here until the test opens the circuit concurrently
                await resume_event.wait()

        task = asyncio.create_task(protected_task())
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        await inside_event.wait()  # Task is now yielded inside protect()

        # Simulate a concurrent coroutine opening the circuit
        cb.force_open()
        assert cb.state == CircuitState.OPEN

        # Resume the protected task — it will exit protect() with no exception
        resume_event.set()
        await task

        # Circuit must still be OPEN
        assert cb.state == CircuitState.OPEN

        # consecutive_failures must NOT have been reset by the stale _record_success
        # call. Without the fix, _record_success resets it to 0.
        assert cb.get_metrics()["consecutive_failures"] == 3


async def _raise_service_error() -> None:
    """Standalone async helper that raises ServiceError (used in P0-2 test)."""
    raise ServiceError("simulated failure")
