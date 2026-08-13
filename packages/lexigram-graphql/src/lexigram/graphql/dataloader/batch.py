"""Batch loading utilities.

This module provides utilities for defining and executing
batch load functions.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Hashable
from typing import (
    Any,
    Generic,
    TypeVar,
)

from lexigram.graphql.exceptions import GraphQLError
from lexigram.logging import get_logger

logger = get_logger(__name__)

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


# Type alias for batch functions
BatchFunction = Callable[[list[K]], Awaitable[list[V | None]]]


def batch_load(
    fn: (
        Callable[[list[K]], Awaitable[list[V]]]
        | Callable[[list[K]], Awaitable[dict[K, V]]]
    ),
    key_fn: Callable[[V], K] | None = None,
) -> BatchFunction[K, V]:
    """Create a batch load function from a loader.

    This decorator/wrapper helps create properly ordered batch
    functions from common data loading patterns.

    Args:
        fn: Function that loads data by keys.
        key_fn: Optional function to extract key from value.

    Returns:
        Batch function that returns values in input order.

    Example:
        ```python
        # From a function returning a list
        @batch_load(key_fn=lambda u: u.id)
        async def load_users(ids: list[str]) -> list[User]:
            return await db.query(User).filter(User.id.in_(ids)).all()

        # From a function returning a dict
        @batch_load
        async def load_users(ids: list[str]) -> dict[str, User]:
            users = await db.query(User).filter(User.id.in_(ids)).all()
            return {u.id: u for u in users}
        ```
    """

    async def wrapper(keys: list[K]) -> list[V | None]:
        try:
            result = await fn(keys)

            # Handle dict result
            if isinstance(result, dict):
                return [result.get(key) for key in keys]

            # Handle list result - need key_fn to map
            if key_fn is not None:
                value_map = {key_fn(v): v for v in result}
                return [value_map.get(key) for key in keys]

            # If no key_fn and list returned, assume same order
            if len(result) == len(keys):
                return list(result)

            raise GraphQLError("Cannot map batch results to keys without key_fn")

        except Exception as _batch_err:  # noqa: BLE001 — batch wrapper must log any error from user-supplied batch functions before re-raising
            logger.exception("Batch load error")
            raise

    return wrapper


class BatchScheduler(Generic[K, V]):
    """Scheduler for batching async operations.

    Collects operations and executes them in batches
    for efficiency.

    Example:
        ```python
        scheduler = BatchScheduler(
            batch_fn=batch_load_users,
            batch_size=50,
            batch_delay_ms=10,
        )

        # Schedule loads
        user1 = await scheduler.schedule("1")
        user2 = await scheduler.schedule("2")
        ```
    """

    def __init__(
        self,
        batch_fn: BatchFunction[K, V],
        batch_size: int = 100,
        batch_delay_ms: float = 2.0,
    ) -> None:
        """Initialize the scheduler.

        Args:
            batch_fn: Batch load function.
            batch_size: Maximum batch size.
            batch_delay_ms: Delay in milliseconds before executing the batch.
                A small non-zero value (default 2ms) allows more keys to accumulate,
                improving efficiency at a slight latency cost.
        """
        self._batch_fn = batch_fn
        self._batch_size = batch_size
        self._batch_delay_ms = batch_delay_ms

        self._pending: list[tuple[K, asyncio.Future[V | None]]] = []
        self._scheduled = False
        self._background_tasks: set[asyncio.Task[Any]] = set()

    async def schedule(self, key: K) -> V | None:
        """Schedule a load operation.

        Args:
            key: Key to load.

        Returns:
            Loaded value.
        """
        future: asyncio.Future[V | None] = asyncio.Future()
        self._pending.append((key, future))

        # Schedule batch execution
        if not self._scheduled:
            self._scheduled = True

            if self._batch_delay_ms > 0:
                await asyncio.sleep(self._batch_delay_ms / 1000)

            task = asyncio.create_task(self._execute())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        # Execute immediately if batch is full
        if len(self._pending) >= self._batch_size:
            await self._execute()

        return await future

    async def _execute(self) -> None:
        """Execute pending batch."""
        self._scheduled = False

        if not self._pending:
            return

        # Get pending items
        items = list(self._pending)
        self._pending = []

        keys = [item[0] for item in items]
        futures = [item[1] for item in items]

        try:
            values = await self._batch_fn(keys)

            for future, value in zip(futures, values, strict=True):
                if not future.done():
                    future.set_result(value)

        except (RuntimeError, TypeError, ValueError) as e:
            # Set exception on ALL pending futures that haven't been resolved
            for future in futures:
                if not future.done():
                    future.set_exception(e)


__all__ = ["BatchFunction", "BatchScheduler", "batch_load"]
