"""Unit tests for the realtime monitor event stream service."""

from __future__ import annotations

import asyncio

import pytest

from ops_console.domain import Severity, SystemEvent
from ops_console.services.event_stream import DEFAULT_QUEUE_CAPACITY, EventStreamService


def make_event(message: str = "hello") -> SystemEvent:
    return SystemEvent(kind="test", message=message, severity=Severity.INFO, source="unit")


async def drain(stream: EventStreamService, first: SystemEvent) -> list[str]:
    """Consume from the stream until the caller's event shows up, then stop."""
    messages: list[str] = []
    async for event in stream.subscribe():
        messages.append(event.message)
        if event is first:
            break
    return messages


@pytest.mark.asyncio
async def test_publish_fans_out_to_many_subscribers() -> None:
    stream = EventStreamService()
    sent = make_event("one")
    t1 = asyncio.create_task(drain(stream, sent))
    t2 = asyncio.create_task(drain(stream, sent))
    await asyncio.sleep(0.05)

    await stream.publish(sent)
    await asyncio.gather(t1, t2)

    assert t1.result() == ["one"]
    assert t2.result() == ["one"]


@pytest.mark.asyncio
async def test_new_subscriber_replays_history_first() -> None:
    stream = EventStreamService()
    sent = make_event("old")
    await stream.publish(sent)

    messages = await drain(stream, sent)

    assert messages == ["old"]


@pytest.mark.asyncio
async def test_history_is_bounded_and_newest_first() -> None:
    stream = EventStreamService(history_size=3)
    for index in range(5):
        await stream.publish(
            SystemEvent(kind="test", message=f"msg-{index}", severity=Severity.INFO, source="u1")
        )
    snapshot = stream.snapshot()

    assert len(snapshot) == 3
    assert [event.message for event in snapshot] == ["msg-4", "msg-3", "msg-2"]


@pytest.mark.asyncio
async def test_slow_consumer_drops_oldest_instead_of_blocking() -> None:
    stream = EventStreamService(history_size=200)
    consumed: list[str] = []
    finished = asyncio.Event()

    async def slow_consumer() -> None:
        async for event in stream.subscribe():
            consumed.append(event.message)
            if len(consumed) >= DEFAULT_QUEUE_CAPACITY:
                break
        finished.set()

    task = asyncio.create_task(slow_consumer())
    await asyncio.sleep(0.05)

    for index in range(300):
        await stream.publish(
            SystemEvent(kind="test", message=f"msg-{index}", severity=Severity.INFO, source="u1")
        )
    await asyncio.wait_for(task, timeout=5)

    # The slow consumer fell behind the queue capacity (100) and never got
    # scheduled mid-publish (the publisher never yields), so the queue kept
    # only the newest 100 events: 200..299. Nothing below 200 is delivered.
    assert set(consumed) == {f"msg-{i}" for i in range(200, 300)}