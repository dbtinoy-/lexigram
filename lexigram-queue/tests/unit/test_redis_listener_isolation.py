"""Tests for per-message isolation in the RedisQueue listener loop.

Regression coverage for the audit finding that a single handler exception
(or malformed payload) permanently killed the per-topic ``_listen()`` task.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.queue.types import BusMessage
import lexigram.serialization as json
from lexigram.testing.fakes import FakeTracer


def _make_queue(**kwargs: Any) -> Any:
    from lexigram.queue.backends.redis import RedisQueue

    return RedisQueue(url="redis://localhost:6379/0", **kwargs)


def _encode_message(message_id: str, topic: str, payload: Any) -> dict[str, Any]:
    """Build a pubsub 'message' raw dict with JSON-encoded data."""
    return {
        "type": "message",
        "data": json.dumps(
            {"id": message_id, "topic": topic, "payload": payload, "headers": {}}
        ),
    }


def _make_pubsub(
    messages: list[dict[str, Any]], keep_alive: asyncio.Event | None = None
) -> MagicMock:
    """Build a fake pubsub that yields the given raw messages.

    When ``keep_alive`` is provided, the fake listener generator stays
    pending after the last message so the test can assert the listener
    task is still alive and running.

    Args:
        messages: Raw pubsub dicts to yield.
        keep_alive: Optional event to await after the last message.
    """
    fake_pubsub = MagicMock()
    fake_pubsub.subscribe = AsyncMock()

    async def fake_listen() -> Any:
        for raw in messages:
            yield raw
        if keep_alive is not None:
            await keep_alive.wait()

    fake_pubsub.listen = fake_listen
    return fake_pubsub


@pytest.mark.asyncio
async def test_poison_message_does_not_kill_listener() -> None:
    """A handler raising on one message must not stop later messages."""
    queue = _make_queue()
    mock_client = MagicMock()
    mock_client.aclose = AsyncMock()
    queue._client = mock_client
    keep_alive = asyncio.Event()
    mock_client.pubsub.return_value = _make_pubsub(
        [
            _encode_message("msg-1", "jobs", {"seq": 1}),
            _encode_message("msg-2", "jobs", {"seq": 2}),
        ],
        keep_alive=keep_alive,
    )

    delivered: list[BusMessage] = []

    async def handler(msg: BusMessage) -> None:
        if msg.payload == {"seq": 1}:
            raise ValueError("poison message")
        delivered.append(msg)

    await queue.subscribe("jobs", handler)
    listen_task = next(
        task for task in queue._tasks if task.get_name() == "redis_queue_msg_jobs"
    )
    await asyncio.sleep(0.1)

    assert len(delivered) == 1
    assert delivered[0].id == "msg-2"
    assert delivered[0].payload == {"seq": 2}
    assert not listen_task.done()

    await queue.close()


@pytest.mark.asyncio
async def test_malformed_payload_does_not_kill_listener() -> None:
    """An undecodable message must not stop later messages."""
    queue = _make_queue()
    mock_client = MagicMock()
    mock_client.aclose = AsyncMock()
    queue._client = mock_client
    keep_alive = asyncio.Event()
    fake_pubsub = MagicMock()
    fake_pubsub.subscribe = AsyncMock()

    async def fake_listen() -> Any:
        yield {"type": "message", "data": "{not json"}
        yield _encode_message("msg-2", "jobs", {"seq": 2})
        await keep_alive.wait()

    fake_pubsub.listen = fake_listen
    mock_client.pubsub.return_value = fake_pubsub

    delivered: list[BusMessage] = []

    async def handler(msg: BusMessage) -> None:
        delivered.append(msg)

    await queue.subscribe("jobs", handler)
    await asyncio.sleep(0.1)

    assert len(delivered) == 1
    assert delivered[0].id == "msg-2"
    assert delivered[0].payload == {"seq": 2}

    await queue.close()


@pytest.mark.asyncio
async def test_poison_message_records_exception_on_span() -> None:
    """A failing handler must mark the receive span as error, not kill the loop."""
    queue = _make_queue()
    mock_client = MagicMock()
    mock_client.aclose = AsyncMock()
    queue._client = mock_client
    tracer = FakeTracer()
    queue.set_tracer(tracer)
    mock_client.pubsub.return_value = _make_pubsub(
        [_encode_message("msg-1", "jobs", {"seq": 1})]
    )

    async def handler(msg: BusMessage) -> None:
        raise RuntimeError("boom")

    await queue.subscribe("jobs", handler)
    await asyncio.sleep(0.1)

    receive_span = tracer.spans[0]
    assert receive_span.name == "queue.receive jobs"
    assert receive_span.status == "error"
    assert receive_span.events[0][0] == "exception"

    await queue.close()


@pytest.mark.asyncio
async def test_messages_processed_concurrently() -> None:
    """Two blocking handlers must run concurrently rather than serially."""
    queue = _make_queue()
    mock_client = MagicMock()
    mock_client.aclose = AsyncMock()
    queue._client = mock_client
    mock_client.pubsub.return_value = _make_pubsub(
        [
            _encode_message("msg-1", "jobs", {"seq": 1}),
            _encode_message("msg-2", "jobs", {"seq": 2}),
        ]
    )

    started: list[str] = []

    async def handler(msg: BusMessage) -> None:
        started.append(msg.id)
        await asyncio.sleep(0.5)

    await queue.subscribe("jobs", handler)
    await asyncio.sleep(0.1)

    assert started == ["msg-1", "msg-2"]

    await queue.close()


__all__: list[str] = []
