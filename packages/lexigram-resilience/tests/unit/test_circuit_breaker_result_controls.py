"""Preset, manual-control, and concurrency-fix tests."""

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



async def _raise_service_error() -> None:
    """Standalone async helper that raises ServiceError (used in P0-2 test)."""
    raise ServiceError("simulated failure")


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


