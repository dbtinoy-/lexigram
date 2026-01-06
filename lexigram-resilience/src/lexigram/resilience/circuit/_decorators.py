"""Decorator helpers for circuit breaker protection on async and sync functions."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, TypeVar, cast

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from lexigram.contracts.infra.resilience.models import CircuitBreakerConfig
    from lexigram.resilience.circuit._registry import CircuitBreakerRegistry

logger = get_logger(__name__)

T = TypeVar("T")


def circuit_breaker(
    name: str,
    registry: CircuitBreakerRegistry,
    config: CircuitBreakerConfig | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Awaitable[T]]]:
    """Decorator to apply circuit breaker protection to a function.

    The registry must be provided explicitly to avoid global state (MAJ-2).
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
    """Synchronous decorator to apply circuit breaker protection to a function.

    The registry must be provided explicitly to avoid global state (MAJ-2).

    Note: This is for sync functions. For async functions, use circuit_breaker.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            import asyncio

            cb = asyncio.run(registry.get_or_create(name, config))
            return cast("T", cb.execute_sync(func, *args, **kwargs))

        return wrapper

    return decorator


__all__ = ["circuit_breaker", "circuit_breaker_sync"]
