"""Fallback, decorator, and context-manager integration tests."""

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


