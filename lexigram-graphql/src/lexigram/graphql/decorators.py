"""Decorators for GraphQL resolvers — retry and structured logging."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import functools
from typing import Any, TypeVar

from lexigram.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

__all__ = [
    "log_resolver",
    "retry_resolver",
]


def retry_resolver(
    max_retries: int = 3,
    *,
    delay: float = 0.1,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Wrap an async GraphQL resolver with automatic retry logic.

    Retries the decorated resolver up to *max_retries* times when any of the
    specified *exceptions* are raised. Uses exponential back-off between
    attempts: ``delay * 2 ** attempt`` seconds.

    Args:
        max_retries: Maximum number of attempts before re-raising the last
            exception. Must be at least 1.
        delay: Base delay in seconds between retries. Doubles on each attempt.
        exceptions: Tuple of exception types that trigger a retry. Defaults
            to ``(Exception,)`` — any exception retries.

    Returns:
        Decorator that wraps an async resolver with retry machinery.

    Example::

        @strawberry.type
        class Query:
            @retry_resolver(max_retries=3, delay=0.2, exceptions=(TimeoutError,))
            async def user(self, info: Info, id: str) -> User:
                return await fetch_user(id)
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            for attempt in range(max_retries):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001
                    last_exc = exc
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (2**attempt))
                    logger.warning(
                        "resolver_retry",
                        resolver=fn.__qualname__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(exc),
                    )
            raise last_exc from last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


def log_resolver(fn: F) -> F:
    """Wrap an async GraphQL resolver with structured entry/exit/error logging.

    Emits debug-level log events on entry and exit, and an error-level event
    when an exception propagates out of the resolver. The exception is always
    re-raised — this decorator never swallows errors.

    Args:
        fn: The async resolver function to wrap.

    Returns:
        Wrapped resolver with structured logging applied.

    Example::

        @strawberry.type
        class Mutation:
            @log_resolver
            async def create_user(self, info: Info, input: CreateUserInput) -> User:
                return await service.create(input)
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.debug("resolver_enter", resolver=fn.__qualname__)
        try:
            result = await fn(*args, **kwargs)
            logger.debug("resolver_exit", resolver=fn.__qualname__)
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "resolver_error",
                resolver=fn.__qualname__,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

    return wrapper  # type: ignore[return-value]
