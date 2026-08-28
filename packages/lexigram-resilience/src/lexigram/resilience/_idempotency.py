"""Idempotency decorator ensuring at-most-once async execution."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any

from lexigram import hashing, serialization
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol

logger = get_logger(__name__)


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
