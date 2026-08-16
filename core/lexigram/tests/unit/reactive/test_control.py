"""Tests for control and combine operators."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from lexigram.reactive import EventStream, Stream, ops


async def gen() -> Any:
    for i in range(10):
        yield i


async def collect(stream: EventStream[Any]) -> list[Any]:
    return [item async for item in stream]


async def test_take_limits_items() -> None:
    assert await collect(Stream(gen()).pipe(ops.take(3))) == [0, 1, 2]


async def test_skip_drops_first_items() -> None:
    assert await collect(Stream(gen()).pipe(ops.skip(7))) == [7, 8, 9]


async def test_merge_interleaves_sources() -> None:
    async def slow() -> Any:
        for x in [1, 2]:
            await asyncio.sleep(0.01)
            yield x

    async def fast() -> Any:
        for x in [10, 20, 30]:
            yield x

    result = await collect(Stream(slow()).pipe(ops.merge(Stream(fast()))))
    assert sorted(result) == [1, 2, 10, 20, 30]


async def test_catch_switches_to_fallback_on_error() -> None:
    async def exploding() -> Any:
        yield 1
        raise RuntimeError("boom")

    async def fallback() -> Any:
        yield 99

    result = await collect(Stream(exploding()).pipe(ops.catch(lambda _e: Stream(fallback()))))
    assert result == [1, 99]


async def test_catch_emits_default_and_stops() -> None:
    async def exploding() -> Any:
        yield 1
        raise RuntimeError("boom")

    result = await collect(Stream(exploding()).pipe(ops.catch(default=-1)))
    assert result == [1, -1]