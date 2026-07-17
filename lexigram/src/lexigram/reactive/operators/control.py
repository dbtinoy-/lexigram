"""Control and combination operators: take, skip, merge, catch."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from typing import Any

from lexigram.reactive.core import EventStream, Stream


def take(count: int) -> Any:
    """Emit at most ``count`` items, then stop the stream.

    Args:
        count: Maximum number of items to emit. ``0`` emits nothing.

    Returns:
        An operator that truncates the stream.
    """

    def _op(source: EventStream[Any]) -> EventStream[Any]:
        async def _gen() -> AsyncIterator[Any]:
            seen = 0
            async for item in source:
                if seen >= count:
                    break
                yield item
                seen += 1

        return Stream(_gen())

    return _op


def skip(count: int) -> Any:
    """Drop the first ``count`` items.

    Args:
        count: Number of initial items to drop.

    Returns:
        An operator that discards leading items.
    """

    def _op(source: EventStream[Any]) -> EventStream[Any]:
        async def _gen() -> AsyncIterator[Any]:
            seen = 0
            async for item in source:
                if seen >= count:
                    yield item
                else:
                    seen += 1

        return Stream(_gen())

    return _op


def merge(*sources: EventStream[Any]) -> Any:
    """Interleave items from multiple source streams.

    Args:
        sources: Additional streams to merge with the piped source.

    Returns:
        An operator merging the piped source with all given sources.
    """

    def _op(source: EventStream[Any]) -> EventStream[Any]:
        all_sources = (source, *sources)

        async def _gen() -> AsyncIterator[Any]:
            queue: asyncio.Queue[Any] = asyncio.Queue()
            remaining = len(all_sources)

            async def _feed(stream: EventStream[Any]) -> None:
                nonlocal remaining
                try:
                    async for item in stream:
                        await queue.put(item)
                except Exception:  # noqa: BLE001 — operator boundary
                    pass
                finally:
                    remaining -= 1
                    if remaining == 0:
                        await queue.put(None)

            tasks = [asyncio.create_task(_feed(s)) for s in all_sources]
            self_tasks: set[asyncio.Task[Any]] = set(tasks)
            for task in tasks:
                self_tasks.add(task)  # keep a strong ref (RUF006)
                task.add_done_callback(self_tasks.discard)
            try:
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    yield item
            finally:
                for task in tasks:
                    task.cancel()
                for task in tasks:
                    with suppress(asyncio.CancelledError):
                        await task

        return Stream(_gen())

    return _op


def catch(
    fallback: Callable[[BaseException], EventStream[Any]] | None = None,
    default: Any = None,
) -> Any:
    """Handle a source error by switching to a fallback or emitting a default.

    Args:
        fallback: Optional callable building a replacement stream from the error.
        default: Value emitted once before the stream ends when no fallback given.

    Returns:
        An operator that recovers from the first downstream error.
    """

    def _op(source: EventStream[Any]) -> EventStream[Any]:
        async def _gen() -> AsyncIterator[Any]:
            try:
                async for item in source:
                    yield item
            except Exception as exc:  # noqa: BLE001 — operator boundary
                if fallback is not None:
                    replacement = fallback(exc)
                    async for item in replacement:
                        yield item
                elif default is not None:
                    yield default

        return Stream(_gen())

    return _op
