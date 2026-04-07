"""Batch and cache data loading to avoid N+1 query problems."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar

from lexigram.concurrency import Parallel
from lexigram.contracts.core import TaskManagerProtocol
from lexigram.di.decorators import inject

K = TypeVar("K")  # Key type
V = TypeVar("V")  # Value type


@inject
class DataLoaderProtocol(Generic[K, V]):
    """
    DataLoaderProtocol implements the batch-loading pattern.
    It collects requests for individual IDs and executes them in a single batch.
    """

    def __init__(
        self,
        batch_fn: Callable[[list[K]], Awaitable[dict[K, V]]],
        task_manager: TaskManagerProtocol,
    ):
        """
        Initialize with a function that takes a list of keys and returns a dict of results.
        """
        self._batch_fn = batch_fn
        self.task_manager = task_manager
        self._cache: dict[K, V] = {}
        self._pending_keys: list[K] = []
        self._pending_futures: dict[K, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def load(self, key: K) -> V:
        """Load a single value by key, batching with others if possible."""
        if key in self._cache:
            return self._cache[key]

        async with self._lock:
            if key not in self._pending_futures:
                self._pending_keys.append(key)
                self._pending_futures[key] = asyncio.get_event_loop().create_future()

                # If this is the first item in the batch, schedule execution
                if len(self._pending_keys) == 1:
                    self.task_manager.create_background_task(self._execute_batch())

            return await self._pending_futures[key]

    async def load_many(self, keys: list[K]) -> list[V]:
        """Load multiple values by keys in a single batch."""
        return await Parallel.gather(*map(self.load, keys))

    async def _execute_batch(self) -> Any:
        """Internal method to execute the pending batch of keys."""
        # Wait a tiny bit to collect more keys
        await asyncio.sleep(0)

        async with self._lock:
            if not self._pending_keys:
                return

            keys_to_fetch = list(self._pending_keys)
            futures_to_resolve = dict(self._pending_futures)

            self._pending_keys.clear()
            self._pending_futures.clear()

        try:
            results = await self._batch_fn(keys_to_fetch)

            for key in keys_to_fetch:
                value = results.get(key)
                self._cache[key] = value  # type: ignore[assignment]
                if not futures_to_resolve[key].done():
                    futures_to_resolve[key].set_result(value)
        except (RuntimeError, ValueError, TypeError, OSError) as e:
            for future in futures_to_resolve.values():
                if not future.done():
                    future.set_exception(e)

    def clear(self, key: K | None = None) -> Any:
        """Clear the cache."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
