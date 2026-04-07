"""Circuit Breaker - Fault tolerance with automatic recovery patterns.

This module implements the circuit breaker pattern to prevent cascading failures
by temporarily stopping calls to failing services and allowing them to recover.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
import functools
from typing import Any, TypeVar, cast

T = TypeVar("T")

from lexigram.contracts.infra.resilience import CircuitState
from lexigram.contracts.infra.resilience.models import CircuitBreakerConfig
from lexigram.contracts.observability.metrics import MetricsRecorderProtocol
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.resilience.circuit._metrics import (
    BucketedSlidingWindowCounter,
    CircuitBreakerMetrics,
)

# CircuitBreakerRegistry is defined below (depends on CircuitBreaker, defined above)
from lexigram.resilience.exceptions import CircuitOpenError

logger = get_logger(__name__)


class CircuitBreaker:
    """Circuit breaker implementation with async support.

    The circuit breaker prevents cascading failures by tracking the health
    of remote service calls. It has three states:

    - **CLOSED**: Normal operation. Requests pass through.
    - **OPEN**: Service is failing. Requests fail immediately without calling
      the remote service.
    - **HALF_OPEN**: After recovery_timeout, limited requests are allowed through
      to test if the service has recovered.

    The circuit opens when the failure threshold is exceeded and closes
    after the success threshold is reached in half-open state.

    Construction
    ------------
    Two equivalent construction styles are supported:

    **Config-first** (preferred for production code and DI-wired providers):
    Construct a :class:`CircuitBreakerConfig` up-front, name it, and share it
    across multiple breakers or register it with a provider.  All individual
    parameters are ignored when *config* is supplied.::

        from lexigram.resilience import CircuitBreaker, CircuitBreakerConfig

        cfg = CircuitBreakerConfig(
            name="external-api",
            failure_threshold=5,
            recovery_timeout=60.0,
        )
        breaker = CircuitBreaker(config=cfg)

    **Using the config object** (recommended for production)::

        from lexigram.resilience import CircuitBreaker, CircuitBreakerConfig

        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            success_threshold=2,
        )
        breaker = CircuitBreaker(config=config)

    Attributes:
        state: Current state of the circuit breaker (CLOSED, OPEN, HALF_OPEN).
        metrics: Current metrics including success/failure counts.

    Example:
        Using as a decorator::

            from lexigram.resilience import circuit_breaker

            @circuit_breaker(name="external-api", failure_threshold=5)
            async def call_external_api():
                response = await http_client.get("/api/data")
                return response.json()

        Using directly::

            from lexigram.resilience import CircuitBreaker, CircuitBreakerConfig

            config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0)
            breaker = CircuitBreaker(config=config)

            async with breaker:
                result = await risky_operation()

            # Or with fallback
            async def fallback():
                return cached_data

            breaker = CircuitBreaker(config=CircuitBreakerConfig(), fallback=fallback)
            result = await breaker.execute(risky_operation)
    """

    def __init__(
        self,
        config: CircuitBreakerConfig,
        fallback: Callable[..., Any] | None = None,
        metrics_collector: MetricsRecorderProtocol | None = None,
        backend: Any | None = None,
    ) -> None:
        """Initialize the circuit breaker.

        Args:
            config: A CircuitBreakerConfig object (required).
            fallback: Optional callable to execute when the circuit is open.
            metrics_collector: Optional metrics collector.
            backend: Optional distributed state backend.
        """
        self.config = config
        # OPT-RES-3: Fallback function to call when circuit is open
        self._fallback = fallback
        # Distributed state backend (None means in-process only)
        self._backend = backend
        self._state = CircuitState.CLOSED
        self._metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()
        # OPT-RES-2: Semaphore to limit to 1 probe request in HALF_OPEN state
        self._half_open_semaphore = asyncio.Semaphore(1)
        self._half_open_success_count = 0
        self._last_attempt_time: float | None = None
        self._metrics_collector = metrics_collector

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics."""
        return self._metrics

    def get_metrics(self) -> dict[str, Any]:
        """Get metrics as a dictionary for backward compatibility."""
        return {
            "name": self.config.name,
            "state": self._state.value,
            "failure_count": self._metrics.failed_calls,
            "success_count": self._metrics.successful_calls,
            "total_calls": self._metrics.total_calls,
            "consecutive_failures": self._metrics.consecutive_failures,
        }

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        if self._state != CircuitState.OPEN:
            return False

        if self._last_attempt_time is None:
            return False  # Circuit was just opened, don't attempt yet

        return (
            ambient_clock.monotonic() - self._last_attempt_time
            >= self.config.recovery_timeout
        )

    def _record_success(self, response_time: float) -> None:
        """Record a successful call."""
        self._metrics.record_success(response_time)

        if self._metrics_collector:
            tags = {"circuit": self.config.name}
            self._metrics_collector.increment("resilience.circuit.calls", tags=tags)
            self._metrics_collector.increment("resilience.circuit.success", tags=tags)

        # Handle state transitions
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_success_count += 1
            if self._half_open_success_count >= self.config.success_threshold:
                self._change_state(CircuitState.CLOSED)
                self._half_open_success_count = 0

    def _record_failure(self, exception: Exception) -> None:
        """Record a failed call."""
        is_timeout = isinstance(exception, TimeoutError)
        self._metrics.record_failure(is_timeout=is_timeout)

        if self._metrics_collector:
            tags = {
                "circuit": self.config.name,
                "error": type(exception).__name__,
                "timeout": str(is_timeout).lower(),
            }
            self._metrics_collector.increment("resilience.circuit.calls", tags=tags)
            self._metrics_collector.increment("resilience.circuit.failure", tags=tags)

        # Handle state transitions
        if self._state == CircuitState.CLOSED:
            # Check both consecutive failures AND sliding window failure rate
            should_open = False
            if self._metrics.consecutive_failures >= self.config.failure_threshold:
                should_open = True

            # Check failure rate if we have enough samples
            if self._metrics.total_calls >= self.config.failure_threshold:
                if self._metrics.failure_rate >= getattr(
                    self.config,
                    "failure_rate_threshold",
                    0.5,
                ):
                    should_open = True

            if should_open:
                self._change_state(CircuitState.OPEN)
        elif self._state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN returns to OPEN
            self._change_state(CircuitState.OPEN)
            self._half_open_success_count = 0

    def _change_state(self, new_state: CircuitState) -> None:
        """Change circuit state."""
        if self._state != new_state:
            logger.info(
                "circuit_breaker_state_change",
                circuit=self.config.name,
                from_state=self._state.value,
                to_state=new_state.value,
            )
            self._state = new_state
            self._metrics.state_changes += 1
            self._metrics.last_state_change = ambient_clock.monotonic()

            if self._metrics_collector:
                self._metrics_collector.gauge(
                    "resilience.circuit.state",
                    value=1.0 if new_state == CircuitState.OPEN else 0.0,
                    tags={"circuit": self.config.name, "state": new_state.value},
                )

            # When opening the circuit, set the attempt time
            if new_state == CircuitState.OPEN:
                self._last_attempt_time = ambient_clock.monotonic()

            # Reset consecutive counts on CLOSING or manual reset, but keep for OPEN observation
            if new_state == CircuitState.CLOSED:
                self._metrics.reset_consecutive_counts()

    async def _call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute an async function with circuit breaker protection."""
        # OPT-RES-2: In HALF_OPEN state, only allow 1 probe request at a time
        if self._state == CircuitState.HALF_OPEN:
            async with self._half_open_semaphore:
                return await self._execute_call(func, *args, **kwargs)
        else:
            return await self._execute_call(func, *args, **kwargs)

    async def _execute_with_fallback(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute with circuit breaker and handle fallback on circuit open."""
        try:
            return await self._call(func, *args, **kwargs)
        except CircuitOpenError:
            # OPT-RES-3: Call fallback if circuit is open and fallback is defined
            if self._fallback is not None:
                logger.info(
                    "Circuit breaker '%s' is OPEN, calling fallback",
                    self.config.name,
                )
                if asyncio.iscoroutinefunction(self._fallback):
                    return await self._fallback(*args, **kwargs)
                return self._fallback(*args, **kwargs)
            raise

    async def _execute_call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute the actual function call with circuit breaker logic."""
        async with self._lock:
            # Check if we should attempt recovery
            if self._state == CircuitState.OPEN and self._should_attempt_reset():
                self._change_state(CircuitState.HALF_OPEN)
                self._last_attempt_time = ambient_clock.monotonic()

            # Check if call is allowed
            if self._state == CircuitState.OPEN:
                msg = f"Circuit breaker '{self.config.name}' is OPEN"
                raise CircuitOpenError(msg)

        # Execute the function with timeout
        start_time = ambient_clock.monotonic()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout,
                )
            else:
                # For sync functions, run in thread pool.
                # run_in_executor only accepts positional *args, so wrap with
                # functools.partial to forward any keyword arguments correctly.
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        functools.partial(func, *args, **kwargs),
                    ),
                    timeout=self.config.timeout,
                )
        except TimeoutError as e:
            async with self._lock:
                self._record_failure(e)
            msg = f"Call timed out after {self.config.timeout}s"
            raise CircuitOpenError(
                msg,
            ) from e
        except self.config.expected_exception as e:
            async with self._lock:
                self._record_failure(e)
            raise
        else:
            response_time = ambient_clock.monotonic() - start_time
            async with self._lock:
                self._record_success(response_time)
            return result

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Awaitable[T]]:
        """Decorator to apply circuit breaker to a function.

        Returns an *awaitable* wrapper for both sync and async functions.
        """
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T:
                return cast(
                    "T",
                    await self._execute_with_fallback(func, *args, **kwargs),
                )

            return async_wrapper

        @functools.wraps(func)
        async def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            return cast("T", await self._execute_with_fallback(func, *args, **kwargs))

        return sync_wrapper

    async def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a callable through the circuit breaker.

        Primary async call interface — accepts both sync and async callables
        and routes them through the internal circuit-state machine.

        Note: typing is widened to ``Any`` to accommodate async callables
        (``Callable[..., Awaitable[T]]``) alongside plain sync ones.
        """
        return await self._execute_with_fallback(func, *args, **kwargs)

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Alias for ``execute`` — satisfies ``CircuitBreakerProtocol.call``."""
        return await self.execute(func, *args, **kwargs)

    @asynccontextmanager
    async def protect(self) -> AsyncGenerator[Any, None]:
        """Context manager to protect a code block."""
        async with self._lock:
            # Check if we should attempt recovery
            if self._state == CircuitState.OPEN and self._should_attempt_reset():
                self._change_state(CircuitState.HALF_OPEN)
                self._last_attempt_time = ambient_clock.monotonic()

            # Check if execution is allowed
            if self._state == CircuitState.OPEN:
                msg = f"Circuit breaker '{self.config.name}' is OPEN"
                raise CircuitOpenError(msg)

        try:
            yield
            # Record success — but only if the circuit is still not OPEN.
            # Between the lock release above and this point, a concurrent coroutine
            # may have recorded enough failures to open the circuit.  Calling
            # _record_success on an already-OPEN circuit would corrupt internal
            # counters (e.g. resetting consecutive_failures to 0) without any
            # corresponding state-machine benefit.
            async with self._lock:
                if self._state != CircuitState.OPEN:
                    self._record_success(0.0)  # No response time for context manager
        except self.config.expected_exception as e:
            async with self._lock:
                self._record_failure(e)
            raise
        except Exception as e:
            # For unexpected exceptions in context manager, still record as failure
            async with self._lock:
                self._record_failure(e)
            raise

    def execute_sync(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a sync function with circuit breaker protection."""
        # 1. State check
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._change_state(CircuitState.HALF_OPEN)
            else:
                if self._fallback:
                    return self._fallback(*args, **kwargs)
                raise CircuitOpenError(f"Circuit '{self.config.name}' is OPEN")

        # 2. Execution
        start_time = ambient_clock.monotonic()
        try:
            result = func(*args, **kwargs)
            self._record_success(ambient_clock.monotonic() - start_time)
            return result
        except Exception as e:
            if any(isinstance(e, ex) for ex in self.config.expected_exception):
                self._record_failure(e)
            raise

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        # For manual operations, we can modify state directly since we're not in a call
        self._change_state(CircuitState.CLOSED)
        self._half_open_success_count = 0
        self._metrics.consecutive_failures = 0
        self._metrics.consecutive_successes = 0

    def force_open(self) -> None:
        """Manually force the circuit breaker to open state."""
        # For manual operations, we can modify state directly since we're not in a call
        self._change_state(CircuitState.OPEN)

    @classmethod
    def sensitive(cls) -> CircuitBreaker:
        """Trip quickly — for critical dependencies.

        Opens after 3 consecutive failures or a 30 % failure rate.  Waits only
        30 s before probing recovery, and requires just 1 probe success to close
        again.  Use for primary databases, auth services, or any dependency
        whose failure should be surfaced to callers as soon as possible.
        """
        return cls(
            config=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                success_threshold=1,
                failure_rate_threshold=0.3,
            )
        )

    @classmethod
    def tolerant(cls) -> CircuitBreaker:
        """Trip slowly — for non-critical or high-volume dependencies.

        Opens only after 10 consecutive failures or a 70 % failure rate.  Waits
        120 s before probing recovery, and requires 5 consecutive probe successes
        before closing.  Use for analytics sinks, notification services, or any
        call whose failures should not immediately surface to callers.
        """
        return cls(
            config=CircuitBreakerConfig(
                failure_threshold=10,
                recovery_timeout=120.0,
                success_threshold=5,
                failure_rate_threshold=0.7,
            )
        )


# Re-export decorator helpers defined in _decorators.py
from lexigram.resilience.circuit._decorators import (  # noqa: E402
    circuit_breaker,
    circuit_breaker_sync,
)
from lexigram.resilience.circuit._registry import CircuitBreakerRegistry

__all__ = [
    "BucketedSlidingWindowCounter",
    "CircuitBreaker",
    "CircuitBreakerMetrics",
    "CircuitBreakerRegistry",
    "circuit_breaker",
    "circuit_breaker_sync",
]
