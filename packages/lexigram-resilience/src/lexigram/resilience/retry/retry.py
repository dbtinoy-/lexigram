"""Unified retry pattern implementation.

Provides ``retry``, ``calculate_delay``, ``should_retry``, and the
``RetryManager`` / ``RetryPolicy`` extensions.  All retry logic lives here;
``lexigram.resilience.retry`` is now fully self-contained.
"""

from __future__ import annotations

import asyncio
import functools
import secrets
import time
from typing import TYPE_CHECKING, Any, TypeVar

from lexigram.contracts.infra.resilience.models import RetryConfig
from lexigram.logging import get_logger
from lexigram.resilience.exceptions import RetryExhaustedError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")
logger = get_logger(__name__)


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
    """Execute an async callable with retry logic.

    Args:
        func: Async callable to retry.
        *args: Positional arguments forwarded to *func*.
        config: Retry configuration.
        **kwargs: Keyword arguments forwarded to *func*.

    Returns:
        First successful return value of *func*.

    Raises:
        RetryExhaustedError: When all attempts have been exhausted.
    """
    last_exception: Exception | None = None
    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)

            should, _reason = should_retry(None, result, attempt, config)
            if should and config.retry_on_result:
                if config.on_retry:
                    try:
                        config.on_retry(attempt + 1, None)
                    except BaseException:
                        logger.exception("Error in retry callback")
                await asyncio.sleep(calculate_delay(attempt, config))
                continue

            return result

        except Exception as exc:
            last_exception = exc
            should, reason = should_retry(exc, None, attempt, config)

            if not should:
                if attempt + 1 >= config.max_attempts:
                    raise RetryExhaustedError(
                        f"Maximum retry attempts ({config.max_attempts}) exceeded: {reason}",
                        attempts=attempt + 1,
                        last_error=exc,
                    ) from exc
                raise

            if config.on_retry:
                try:
                    config.on_retry(attempt + 1, exc)
                except BaseException:
                    logger.exception("Error in retry callback")

            if attempt + 1 < config.max_attempts:
                delay = calculate_delay(attempt, config)
                logger.warning(
                    "retry_attempt_failed",
                    attempt=attempt + 1,
                    delay=round(delay, 2),
                    func=getattr(func, "__name__", str(func)),
                    error=str(exc),
                    reason=reason,
                )
                await asyncio.sleep(delay)

    raise RetryExhaustedError(
        f"Maximum retry attempts ({config.max_attempts}) exceeded",
        attempts=config.max_attempts,
        last_error=last_exception,
    ) from last_exception


def _retry_sync(
    func: Callable[..., T],
    *args: Any,
    config: RetryConfig,
    **kwargs: Any,
) -> T:
    """Execute a sync callable with retry logic.

    Args:
        func: Sync callable to retry.
        *args: Positional arguments forwarded to *func*.
        config: Retry configuration.
        **kwargs: Keyword arguments forwarded to *func*.

    Returns:
        First successful return value of *func*.

    Raises:
        RetryExhaustedError: When all attempts have been exhausted.
    """
    last_exception: Exception | None = None
    for attempt in range(config.max_attempts):
        try:
            result = func(*args, **kwargs)

            should, _reason = should_retry(None, result, attempt, config)
            if should and config.retry_on_result:
                if config.on_retry:
                    try:
                        config.on_retry(attempt + 1, None)
                    except BaseException:
                        logger.exception("Error in retry callback")
                time.sleep(calculate_delay(attempt, config))
                continue

            return result

        except Exception as exc:
            last_exception = exc
            should, reason = should_retry(exc, None, attempt, config)

            if not should:
                if attempt + 1 >= config.max_attempts:
                    raise RetryExhaustedError(
                        f"Maximum retry attempts ({config.max_attempts}) exceeded: {reason}",
                        attempts=attempt + 1,
                        last_error=exc,
                    ) from exc
                raise

            if config.on_retry:
                try:
                    config.on_retry(attempt + 1, exc)
                except BaseException:
                    logger.exception("Error in retry callback")

            if attempt + 1 < config.max_attempts:
                delay = calculate_delay(attempt, config)
                logger.warning(
                    "retry_attempt_failed",
                    attempt=attempt + 1,
                    delay=round(delay, 2),
                    func=getattr(func, "__name__", str(func)),
                    error=str(exc),
                    reason=reason,
                )
                time.sleep(delay)

    raise RetryExhaustedError(
        f"Maximum retry attempts ({config.max_attempts}) exceeded",
        attempts=config.max_attempts,
        last_error=last_exception,
    ) from last_exception


def retry(
    func_or_config: Callable[..., Awaitable[T] | T] | RetryConfig,
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> Any:
    """Unified retry API for sync and async callables.

    **Decorator mode** (pass ``RetryConfig`` first)::

        config = RetryConfig(max_attempts=3)

        @retry(config)
        async def fetch_data() -> bytes: ...

    **Direct-call mode**::

        result = await retry(fetch_data, config=config)

    Args:
        func_or_config: A :class:`~lexigram.contracts.infra.resilience.RetryConfig`
            (decorator mode) or a callable to invoke with retries (direct-call
            mode).
        *args: Positional arguments forwarded to the callable in direct-call mode.
        config: Required in direct-call mode. Ignored in decorator mode.
        **kwargs: Keyword arguments forwarded to the callable in direct-call mode.

    Returns:
        In decorator mode: a decorator wrapping a callable with retry logic.
        In direct-call mode: the return value of the callable.
    """
    if isinstance(func_or_config, RetryConfig):
        _config = func_or_config

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            is_async = asyncio.iscoroutinefunction(func) or (
                hasattr(func, "__wrapped__")
                and asyncio.iscoroutinefunction(func.__wrapped__)
            )

            @functools.wraps(func)
            async def async_wrapper(*a: Any, **kw: Any) -> Any:
                return await _retry(func, *a, config=_config, **kw)

            @functools.wraps(func)
            def sync_wrapper(*a: Any, **kw: Any) -> Any:
                return _retry_sync(func, *a, config=_config, **kw)

            return async_wrapper if is_async else sync_wrapper

        return decorator

    if not callable(func_or_config):
        raise TypeError(f"Expected callable or RetryConfig, got {type(func_or_config)}")
    if config is None:
        raise ValueError("config must be provided when calling retry() as a function")
    return _retry(func_or_config, *args, config=config, **kwargs)  # type: ignore[arg-type]


class RetryManager:
    """Manager for retry operations with metrics tracking."""

    def __init__(
        self,
        config: RetryConfig,
    ) -> None:
        """Initialize RetryManager.

        Args:
            config: RetryConfig object (required).
        """
        self.config = config

        self.total_attempts = 0
        self.total_successes = 0
        self.total_failures = 0
        self.total_retries = 0

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute async function with retries and track metrics."""
        self.total_attempts += 1
        try:
            result: T = await retry(func, *args, config=self.config, **kwargs)  # type: ignore[arg-type]
            self.total_successes += 1
            return result
        except RetryExhaustedError as e:
            self.total_failures += 1
            self.total_retries += (e.attempts - 1) if e.attempts else 0
            raise
        except BaseException:
            self.total_failures += 1
            raise

    def get_stats(self) -> dict[str, Any]:
        """Get execution statistics."""
        return {
            "total_attempts": self.total_attempts,
            "successes": self.total_successes,
            "failures": self.total_failures,
            "total_retries": self.total_retries,
        }

    def run_sync(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run a sync function with retries (metrics not tracked for sync yet)."""
        return _retry_sync(func, *args, config=self.config, **kwargs)

    def decorate(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Return a decorator using this manager's config."""
        decorator: Callable[[Callable[..., Any]], Callable[..., Any]] = retry(
            self.config
        )
        return decorator


class RetryPolicy:
    """Policy wrapper for retries, used by the resilience pipeline."""

    def __init__(self, config: RetryConfig) -> None:
        self.config = config

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute an async function with retries."""
        result: T = await retry(func, *args, config=self.config, **kwargs)  # type: ignore[arg-type]
        return result

    @classmethod
    def aggressive(cls) -> RetryPolicy:
        """Retry quickly — for fast, idempotent operations.

        5 attempts with a short 100 ms base delay, 1.5× backoff, and a 2 s cap.
        Use for lightweight read operations, DNS lookups, or any call that is
        cheap to repeat and very unlikely to have side-effects.
        """
        return cls(
            RetryConfig(
                max_attempts=5,
                base_delay=0.1,
                max_delay=2.0,
                backoff_factor=1.5,
                jitter=True,
            )
        )

    @classmethod
    def conservative(cls) -> RetryPolicy:
        """Retry slowly — for expensive or non-idempotent operations.

        3 attempts with a 2 s base delay, 2× backoff, and a 30 s cap.
        Use for database writes, payment APIs, or any call where rapid
        retrying could worsen the situation.
        """
        return cls(
            RetryConfig(
                max_attempts=3,
                base_delay=2.0,
                max_delay=30.0,
                backoff_factor=2.0,
                jitter=True,
            )
        )


__all__ = [
    "RetryManager",
    "RetryPolicy",
    "calculate_delay",
    "retry",
    "should_retry",
]
