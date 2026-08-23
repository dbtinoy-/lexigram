"""Resilience pattern decorators with unified sync/async support.

Provides bulkhead, circuit breaker, retry, and timeout decorators.
Import directly from ``lexigram.resilience`` for the canonical API.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import secrets
import time
from typing import TYPE_CHECKING, Any, TypeVar, cast

from lexigram.contracts.infra.resilience.models import (
    CircuitBreakerConfig,
    RetryConfig,
    TimeoutConfig,
)
from lexigram.logging import get_logger
from lexigram.resilience.bulkhead.limiter import Bulkhead, BulkheadConfig
from lexigram.resilience.circuit._registry import CircuitBreakerRegistry
from lexigram.resilience.circuit.timeout import timeout_context
from lexigram.resilience.exceptions import RetryExhaustedError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")

logger = get_logger(__name__)


# ============================================================================
# Bulkhead Decorator
# ============================================================================


def _is_async_function(func: Callable[..., Any]) -> bool:
    """Check if a function is async (coroutine function)."""
    return inspect.iscoroutinefunction(func) or (
        hasattr(func, "__wrapped__") and inspect.iscoroutinefunction(func.__wrapped__)
    )


def bulkhead(
    config: BulkheadConfig,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to apply bulkhead pattern.

    Limits the number of concurrent executions of the decorated function.
    Auto-detects if the decorated function is sync or async and handles
    accordingly.

    Args:
        config: Bulkhead configuration specifying concurrency limits.

    Returns:
        A decorator that wraps the function with bulkhead protection.

    Example:
        from lexigram.resilience import bulkhead, BulkheadConfig

        config = BulkheadConfig(max_concurrent=5)
        @bulkhead(config)
        async def api_call():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if _is_async_function(func):
            bh = Bulkhead(config)

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T:
                return await bh.execute(
                    cast("Callable[..., Awaitable[T]]", func), *args, **kwargs
                )

            return cast("Callable[..., T]", async_wrapper)

        bh = Bulkhead(config)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            return bh.execute_sync(func, *args, **kwargs)

        return cast("Callable[..., T]", sync_wrapper)

    return decorator


# ============================================================================
# Timeout Decorator
# ============================================================================


def with_timeout(
    config: TimeoutConfig,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to apply timeout to a function.

    Auto-detects if the decorated function is sync or async and handles
    accordingly.

    Args:
        config: Timeout configuration specifying duration and behavior.

    Returns:
        A decorator that wraps the function with a timeout guard.

    Example:
        from lexigram.resilience import with_timeout, TimeoutConfig

        config = TimeoutConfig(timeout=5.0)
        @with_timeout(config)
        async def slow_operation():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if inspect.iscoroutinefunction(func) or (
            hasattr(func, "__wrapped__")
            and inspect.iscoroutinefunction(func.__wrapped__)
        ):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T:
                async with timeout_context(config):
                    result: T = await func(*args, **kwargs)  # type: ignore[misc]
                    return result

            return cast("Callable[..., T]", async_wrapper)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)

        return cast("Callable[..., T]", sync_wrapper)

    return decorator


# ============================================================================
# Circuit Breaker Decorators
# ============================================================================


def circuit_breaker(
    name: str,
    registry: CircuitBreakerRegistry,
    config: CircuitBreakerConfig | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Awaitable[T]]]:
    """Decorator to apply circuit breaker protection to an async function.

    The registry must be provided explicitly to avoid global state.

    Args:
        name: Name of the circuit breaker (must match registry).
        registry: CircuitBreakerRegistry instance for managing breakers.
        config: Optional configuration for the circuit breaker.

    Returns:
        A decorator that wraps the async function with circuit breaker protection.

    Example:
        from lexigram.resilience import circuit_breaker, CircuitBreakerRegistry

        registry = CircuitBreakerRegistry()
        @circuit_breaker("api", registry)
        async def api_call():
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            cb = await registry.get_or_create(name, config)
            return cast("T", await cb.execute(func, *args, **kwargs))

        return wrapper

    return decorator


def circuit_breaker_sync(
    name: str,
    registry: CircuitBreakerRegistry,
    config: CircuitBreakerConfig | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., T]]:
    """Decorator to apply circuit breaker protection to a sync function.

    The registry must be provided explicitly to avoid global state.

    Note:
        This is for sync functions. For async functions, use circuit_breaker.

    Args:
        name: Name of the circuit breaker (must match registry).
        registry: CircuitBreakerRegistry instance for managing breakers.
        config: Optional configuration for the circuit breaker.

    Returns:
        A decorator that wraps the sync function with circuit breaker protection.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            cb = asyncio.run(registry.get_or_create(name, config))
            return cb.execute_sync(func, *args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Retry Decorator
# ============================================================================


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for a retry attempt using exponential backoff and optional jitter.

    Args:
        attempt: Zero-based attempt index.
        config: Retry configuration providing base_delay, backoff_factor, max_delay, jitter.

    Returns:
        Delay in seconds (always >= 0).
    """
    delay = config.base_delay * (config.backoff_factor**attempt)
    delay = min(delay, config.max_delay)

    if config.jitter:
        jitter_factor = (
            0.25 if isinstance(config.jitter, bool) else float(config.jitter)
        )
        jitter_range = delay * jitter_factor
        delay += secrets.SystemRandom().uniform(-jitter_range, jitter_range)

    return max(0.0, delay)


def should_retry(
    error: Exception | None,
    result: Any,
    attempt: int,
    config: RetryConfig,
) -> tuple[bool, str]:
    """Decide whether an operation should be retried.

    Args:
        error: The exception raised by the last attempt, or ``None`` if it
            returned a value.
        result: The return value from the last attempt, or ``None`` on exception.
        attempt: Zero-based index of the completed attempt.
        config: Retry configuration.

    Returns:
        A ``(should_retry, reason)`` tuple.
    """
    if attempt + 1 >= config.max_attempts:
        return False, "max_attempts_exceeded"

    if result is not None and config.abort_if is not None:
        if config.abort_if(result):
            return False, "abort_if: result matches abort condition"

    if error is not None and config.abort_on and isinstance(error, config.abort_on):
        return False, f"abort_on: {type(error).__name__}"

    if result is not None and config.retry_on_result:
        return (
            (True, "retry_on_result")
            if config.retry_on_result(result)
            else (False, "result_not_retryable")
        )

    if result is not None:
        # Successful result with no retry_on_result predicate — do not retry.
        return False, "success"

    if error is not None:
        if not isinstance(error, config.retry_on):
            return False, f"exception_not_in_retry_on: {type(error).__name__}"
        if config.retry_if and not config.retry_if(error):
            return False, "retry_if_returned_false"

    return True, "default"


async def _retry(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig,
    **kwargs: Any,
) -> T:
    """Execute an async callable with retry logic."""
    last_error: Exception | None = None
    last_result: Any = None

    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)
            should, _ = should_retry(None, result, attempt, config)
            if not should:
                return result
            last_result = result
        except Exception as e:
            last_error = e
            should, _ = should_retry(e, None, attempt, config)
            if not should:
                if config.exhausted_is_error:  # type: ignore[attr-defined]
                    raise RetryExhaustedError(
                        f"Retry exhausted after {attempt + 1} attempts",
                        attempts=attempt + 1,
                        last_error=e,
                    ) from e
                raise

        if attempt < config.max_attempts - 1:
            delay = calculate_delay(attempt, config)
            logger.debug(
                "retry.attempt",
                attempt=attempt + 1,
                max_attempts=config.max_attempts,
                delay=delay,
                last_error=str(last_error),
                last_result=str(last_result)[:100] if last_result else None,
            )
            await asyncio.sleep(delay)

    if last_error is not None and config.exhausted_is_error:  # type: ignore[attr-defined]
        raise RetryExhaustedError(
            f"Retry exhausted after {config.max_attempts} attempts",
            attempts=config.max_attempts,
            last_error=last_error,
        ) from last_error

    if last_result is not None:
        final: T = last_result
        return final

    raise RetryExhaustedError(
        f"Retry exhausted after {config.max_attempts} attempts",
        attempts=config.max_attempts,
    )


def _retry_sync(
    func: Callable[..., T],
    *args: Any,
    config: RetryConfig,
    **kwargs: Any,
) -> T:
    """Execute a sync callable with retry logic."""
    last_error: Exception | None = None
    last_result: Any = None

    for attempt in range(config.max_attempts):
        try:
            result = func(*args, **kwargs)
            should, _ = should_retry(None, result, attempt, config)
            if not should:
                return result
            last_result = result
        except Exception as e:
            last_error = e
            should, _ = should_retry(e, None, attempt, config)
            if not should:
                if config.exhausted_is_error:  # type: ignore[attr-defined]
                    raise RetryExhaustedError(
                        f"Retry exhausted after {attempt + 1} attempts",
                        attempts=attempt + 1,
                        last_error=e,
                    ) from e
                raise

        if attempt < config.max_attempts - 1:
            delay = calculate_delay(attempt, config)
            logger.debug(
                "retry.attempt",
                attempt=attempt + 1,
                max_attempts=config.max_attempts,
                delay=delay,
                last_error=str(last_error),
                last_result=str(last_result)[:100] if last_result else None,
            )
            time.sleep(delay)

    if last_error is not None and config.exhausted_is_error:  # type: ignore[attr-defined]
        raise RetryExhaustedError(
            f"Retry exhausted after {config.max_attempts} attempts",
            attempts=config.max_attempts,
            last_error=last_error,
        ) from last_error

    if last_result is not None:
        final: T = last_result
        return final

    raise RetryExhaustedError(
        f"Retry exhausted after {config.max_attempts} attempts",
        attempts=config.max_attempts,
    )


def retry(
    config: RetryConfig | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to apply retry logic to a function.

    Auto-detects if the decorated function is sync or async and handles
    accordingly.

    Args:
        config: Retry configuration. If None, uses default RetryConfig().

    Returns:
        A decorator that wraps the function with retry protection.

    Example:
        from lexigram.resilience import retry, RetryConfig

        config = RetryConfig(max_attempts=3, base_delay=1.0)
        @retry(config)
        async def unreliable_api_call():
            ...
    """
    cfg = config or RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if inspect.iscoroutinefunction(func) or (
            hasattr(func, "__wrapped__")
            and inspect.iscoroutinefunction(func.__wrapped__)
        ):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T:
                return await _retry(
                    cast("Callable[..., Awaitable[T]]", func),
                    *args,
                    config=cfg,
                    **kwargs,
                )

            return cast("Callable[..., T]", async_wrapper)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            return _retry_sync(func, *args, config=cfg, **kwargs)

        return cast("Callable[..., T]", sync_wrapper)

    return decorator


__all__ = [
    "bulkhead",
    "circuit_breaker",
    "circuit_breaker_sync",
    "calculate_delay",
    "idempotent",
    "retry",
    "should_retry",
    "with_timeout",
]


# ============================================================================
# Idempotency Decorator
# ============================================================================

from lexigram import hashing, serialization  # type: ignore[attr-defined]

if TYPE_CHECKING:
    from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol


def idempotent(
    store: IdempotencyStoreProtocol,
    *,
    key_func: Callable[..., str] | None = None,
    ttl: float | None = 3600.0,
) -> Callable[..., Any]:
    """Decorator that ensures an async function executes at most once per key.

    The idempotency key is derived from function arguments by default,
    or from a custom key_func. Results are cached in the provided store.

    Args:
        store: The IdempotencyStoreProtocol backend for caching results.
        key_func: Optional callable that generates a key string from (*args, **kwargs).
            If None, a deterministic hash of the arguments is used.
        ttl: Time-to-live in seconds for cached results. Defaults to 3600 (1 hour).

    Returns:
        A decorator that wraps async functions with idempotency logic.

    Example:
        from lexigram.resilience import idempotent, InMemoryIdempotencyStore

        store = InMemoryIdempotencyStore()

        @idempotent(store, ttl=60.0)
        async def create_order(order_id: str, amount: float) -> dict:
            return {"id": order_id, "amount": amount}
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if key_func is not None:
                key = key_func(*args, **kwargs)
            else:
                key = _idempotent_default_key(func, args, kwargs)

            if len(key) > 256:
                msg = f"Idempotency key exceeds maximum length of 256 characters: {len(key)}"
                raise ValueError(msg)

            cached: Any = await store.get(key)
            if cached is not None:
                logger.debug(
                    "idempotency.cache_hit",
                    key=key,
                    function=func.__qualname__,
                )
                return cached

            ttl_int = int(ttl) if ttl is not None else 3600
            acquired = await store.acquire(key, ttl_int)
            if not acquired:
                logger.debug(
                    "idempotency.already_claimed",
                    key=key,
                    function=func.__qualname__,
                )
                return await store.get(key)

            result = await func(*args, **kwargs)
            await store.set(key, result, ttl=ttl)
            logger.debug(
                "idempotency.executed",
                key=key,
                function=func.__qualname__,
            )
            return result

        return wrapper

    return decorator


def _idempotent_default_key(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    """Generate a deterministic idempotency key from function identity and arguments."""
    raw = serialization.dumps(
        {
            "func": func.__qualname__,
            "args": [repr(a) for a in args],
            "kwargs": {k: repr(v) for k, v in sorted(kwargs.items())},
        },
        sort_keys=True,
    )
    return str(hashing.hash_hex(raw))
