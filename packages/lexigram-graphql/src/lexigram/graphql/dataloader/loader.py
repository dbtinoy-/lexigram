"""DataLoaderProtocol implementation.

This module provides a DataLoaderProtocol implementation for batching
and caching data fetches in GraphQL resolvers to solve the N+1 problem.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Hashable, Sequence
from typing import (
    Generic,
    TypeVar,
)

from lexigram.graphql.config import DataLoaderConfig
from lexigram.graphql.dataloader.cache import InMemoryCache, LoaderCache
from lexigram.logging import get_logger

logger = get_logger(__name__)

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class DataLoaderProtocol(Generic[K, V]):
    """DataLoaderProtocol for batching and caching.

    DataLoaderProtocol is a utility for batching and caching data fetches
    to efficiently resolve GraphQL queries and avoid the N+1 problem.

    Example:
        ```python
        async def batch_load_users(ids: list[str]) -> list[User | None]:
            users = await db.get_users_by_ids(ids)
            # Return in same order as input ids
            user_map = {u.id: u for u in users}
            return list(map(lambda id: user_map.get(id), ids))

        loader = DataLoaderProtocol(batch_load_users)

        # These will be batched into a single call
        user1 = await loader.load("1")
        user2 = await loader.load("2")
        ```
    """

    def __init__(
        self,
        batch_fn: Callable[[list[K]], Awaitable[list[V | None]]],
        config: DataLoaderConfig | None = None,
        cache: LoaderCache[K, V] | None = None,
    ) -> None:
        """Initialize the DataLoaderProtocol.

        Args:
            batch_fn: Function that loads a batch of values by keys.
            config: DataLoaderProtocol configuration.
            cache: Optional cache implementation.
        """
        self._batch_fn = batch_fn
        self._config = config or DataLoaderConfig()
        self._cache = cache if cache is not None else InMemoryCache[K, V]()

        # Thread-safe state
        self._lock = asyncio.Lock()
        self._pending: dict[K, asyncio.Future[V | None]] = {}
        self._dispatch_task: asyncio.Task[None] | None = None

    @property
    def config(self) -> DataLoaderConfig:
        """Get configuration."""
        return self._config

    async def load(self, key: K) -> V | None:
        """Load a value by key.

        The load will be batched with other loads that occur
        in the same tick of the event loop.

        Args:
            key: The key to load.

        Returns:
            The loaded value or None if not found.

        Raises:
            DataLoaderError: If loading fails.
        """
        # Check cache first
        if self._config.cache_enabled and self._cache.has(key):
            return self._cache.get(key)

        # Acquire lock for pending dict
        async with self._lock:
            # Check if already pending
            if key in self._pending:
                future = self._pending[key]
            else:
                # Create new future
                future = asyncio.Future[V | None]()
                self._pending[key] = future

                # Schedule dispatch if not already scheduled
                if self._dispatch_task is None or self._dispatch_task.done():
                    self._dispatch_task = asyncio.create_task(self._dispatch_batch())
                    logger.debug("DataLoaderProtocol dispatch task scheduled")

        # Wait for result (outside lock)
        return await future

    async def load_many(self, keys: Sequence[K]) -> list[V | None]:
        """Load multiple values by keys.

        Args:
            keys: List of keys to load.

        Returns:
            List of values in the same order as keys.
        """
        return await asyncio.gather(*[self.load(key) for key in keys])

    async def _dispatch_batch(self) -> None:
        """Dispatch the pending batch."""
        # Extract pending items (thread-safe)
        async with self._lock:
            if not self._pending:
                return

            # Get all pending keys
            keys = list(self._pending.keys())
            futures = dict(self._pending)

            # Clear pending (others can add new ones)
            self._pending.clear()

            logger.debug("DataLoaderProtocol dispatching batch of %d keys", len(keys))

        # Respect max batch size (outside lock)
        if self._config.max_batch_size > 0:
            # Split into chunks if needed
            for i in range(0, len(keys), self._config.max_batch_size):
                chunk_keys = keys[i : i + self._config.max_batch_size]
                chunk_futures = {k: futures[k] for k in chunk_keys}
                await self._execute_batch(chunk_keys, chunk_futures)
        else:
            await self._execute_batch(keys, futures)

    async def _execute_batch(
        self,
        keys: list[K],
        futures: dict[K, asyncio.Future[V | None]],
    ) -> None:
        """Execute a batch load.

        Args:
            keys: Keys to load in this batch.
            futures: Futures to resolve for these keys.
        """
        try:
            # Execute batch function
            values = await self._batch_fn(keys)

            # Validate response
            if len(values) != len(keys):
                raise ValueError(
                    f"batch_fn returned {len(values)} values for {len(keys)} keys. "
                    f"Must return same number of values as keys (use None for missing).",
                )

            # Resolve futures and cache results
            for key, value in zip(keys, values, strict=True):
                if self._config.cache_enabled and value is not None:
                    self._cache.set(key, value)

                future = futures[key]
                if not future.done():
                    future.set_result(value)

            logger.debug("DataLoaderProtocol batch completed successfully")

        except Exception as e:  # noqa: BLE001 — dataloader must propagate any batch error to all pending futures
            # Reject all pending futures
            logger.error("DataLoaderProtocol batch failed: %s", e, exc_info=True)

            for future in futures.values():
                if not future.done():
                    future.set_exception(e)

    def prime(self, key: K, value: V) -> None:
        """Prime the cache with a value.

        Use this to add values to the cache that were loaded
        through other means.

        Args:
            key: The key.
            value: The value to cache.
        """
        if self._config.cache_enabled:
            self._cache.set(key, value)

    def clear(self, key: K) -> None:
        """Clear a cached value.

        Args:
            key: The key to clear.
        """
        self._cache.delete(key)

    def clear_all(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


def create_loader(
    batch_fn: Callable[[list[K]], Awaitable[list[V | None]]],
    batch_size: int = 100,
    cache_enabled: bool = True,
) -> DataLoaderProtocol[K, V]:
    """Create a DataLoaderProtocol (convenience function).

    Args:
        batch_fn: Batch load function.
        batch_size: Maximum batch size.
        cache_enabled: Whether to enable caching.

    Returns:
        Configured DataLoaderProtocol.

    Example:
        ```python
        user_loader = create_loader(
            batch_load_users,
            batch_size=50,
        )

        user = await user_loader.load("123")
        ```
    """
    config = DataLoaderConfig(
        max_batch_size=batch_size,
        cache_enabled=cache_enabled,
    )
    return DataLoaderProtocol(batch_fn, config=config)


__all__ = ["DataLoaderProtocol", "create_loader"]
