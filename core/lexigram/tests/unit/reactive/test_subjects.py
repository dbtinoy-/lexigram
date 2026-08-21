"""Tests for hot subjects and sharing."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from lexigram.reactive import EventStream, Stream, Subject, share


async def collect_until(stream: EventStream[Any], count: int) -> list[Any]:
    items: list[Any] = []
    async for item in stream:
        items.append(item)
        if len(items) >= count:
            break
    return items


async def test_subject_fans_out_to_subscribers() -> None:
    subject = Subject[int]()
    received_a: list[int] = []
    received_b: list[int] = []

    async def consume_a() -> None:
        async for item in subject:
            received_a.append(item)

    async def consume_b() -> None:
        async for item in subject:
            received_b.append(item)

    task_a = asyncio.create_task(consume_a())
    task_b = asyncio.create_task(consume_b())
    await asyncio.sleep(0.01)
    for i in range(3):
        await subject.publish(i)
    await asyncio.sleep(0.01)
    await subject.complete()
    await asyncio.gather(task_a, task_b)
    assert received_a == [0, 1, 2]
    assert received_b == [0, 1, 2]


async def test_share_runs_source_into_subject() -> None:
    async def gen() -> Any:
        for i in range(3):
            yield i
            await asyncio.sleep(0.01)

    subject = share(Stream(gen()))
    items = await collect_until(subject, 3)
    assert items == [0, 1, 2]
    await subject.complete()


async def test_share_is_hot_between_publishes() -> None:
    async def gen() -> Any:
        yield "first"
        await asyncio.sleep(0.05)
        yield "second"

    subject = share(Stream(gen()))
    await asyncio.sleep(0.02)  # "first" already published
    got = await collect_until(subject, 1)
    assert got == ["second"]


async def test_subject_error_terminates_subscribers_with_exception() -> None:
    subject: Subject[int] = Subject()
    received: list[int] = []

    async def consume() -> None:
        try:
            async for item in subject:
                received.append(item)
        except ValueError as exc:
            received.append(-1)  # marker
            assert str(exc) == "bad"

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.01)

    await subject.publish(1)
    await subject.publish(2)
    await subject.error(ValueError("bad"))
    await asyncio.wait_for(task, timeout=2)

    assert received == [1, 2, -1]
    # publish after error is a no-op, not an explosion
    await subject.publish(3)
    assert received == [1, 2, -1]


async def test_share_propagates_pump_errors_to_subscribers() -> None:
    async def failing_source() -> AsyncIterator[int]:
        yield 1
        raise RuntimeError("pump died")

    subject = share(Stream(failing_source()))

    received: list[int] = []

    async def drain() -> None:
        async for item in subject:
            received.append(item)

    with pytest.raises(RuntimeError, match="pump died"):
        await drain()

    assert received == [1]