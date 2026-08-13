"""Tests for distributed tracing in queue backends."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Self
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.queue.types import BusMessage
from lexigram.testing.fakes import FakeTracer


@pytest.mark.asyncio
async def test_memory_queue_publish_injects_traceparent() -> None:
    """Memory queue publish should record a span via the tracer."""
    from lexigram.queue.backends.memory import InMemoryQueue

    tracer = FakeTracer()
    queue = InMemoryQueue()
    queue.set_tracer(tracer)

    await queue.publish("jobs", BusMessage(topic="jobs", payload={"id": 1}))

    assert tracer.spans[0].name == "queue.publish jobs"


@pytest.mark.asyncio
async def test_memory_queue_publish_injects_trace_context_into_headers() -> None:
    """Memory queue publish should inject trace context into message headers."""
    from lexigram.queue.backends.memory import InMemoryQueue

    tracer = FakeTracer()
    queue = InMemoryQueue()
    queue.set_tracer(tracer)

    span = tracer.start_span("test.span")
    with span:
        message = BusMessage(
            topic="jobs", payload={"id": 1}, headers={"custom": "header"}
        )
        updated_message = await queue.publish("jobs", message)

        assert updated_message.headers is not None
        assert "traceparent" in updated_message.headers
        assert "custom" in updated_message.headers
        assert updated_message.headers["custom"] == "header"


@pytest.mark.asyncio
async def test_memory_queue_no_tracer_publishes_without_span() -> None:
    """Memory queue publish without tracer should work silently."""
    from lexigram.queue.backends.memory import InMemoryQueue

    queue = InMemoryQueue()
    await queue.publish("jobs", BusMessage(topic="jobs", payload={"id": 1}))


@pytest.mark.asyncio
async def test_memory_queue_set_tracer_clears() -> None:
    """set_tracer(None) should clear the tracer."""
    from lexigram.queue.backends.memory import InMemoryQueue

    tracer = FakeTracer()
    queue = InMemoryQueue()
    queue.set_tracer(tracer)
    queue.set_tracer(None)

    await queue.publish("jobs", BusMessage(topic="jobs", payload={"id": 1}))

    assert len(tracer.spans) == 0


@pytest.mark.asyncio
async def test_memory_queue_subscribe_wraps_handler_in_span() -> None:
    """Memory queue subscribe should wrap handler execution in a receive span."""
    from lexigram.queue.backends.memory import InMemoryQueue

    tracer = FakeTracer()
    queue = InMemoryQueue()
    await queue.connect()
    queue.set_tracer(tracer)

    handler_called = False

    async def handler(msg: BusMessage) -> None:
        nonlocal handler_called
        handler_called = True

    await queue.subscribe("jobs", handler)

    await queue.publish("jobs", BusMessage(topic="jobs", payload={"id": 1}))

    await asyncio.sleep(0.1)

    assert len(tracer.spans) >= 2
    assert tracer.spans[0].name == "queue.publish jobs"
    assert tracer.spans[1].name == "queue.receive jobs"
    assert handler_called

    await queue.close()


@pytest.mark.asyncio
async def test_memory_queue_receive_links_parent_context() -> None:
    """Memory queue receive span should inherit trace ID from published message.

    This verifies that when a message contains a traceparent header, the
    receive span continues the same trace (same trace_id, new span_id).
    """
    from lexigram.queue.backends.memory import InMemoryQueue

    tracer = FakeTracer()
    queue = InMemoryQueue()
    await queue.connect()
    queue.set_tracer(tracer)

    received_message = None

    async def handler(msg: BusMessage) -> None:
        nonlocal received_message
        received_message = msg

    await queue.subscribe("jobs", handler)

    span = tracer.start_span("test.setup")
    with span:
        message = BusMessage(
            topic="jobs", payload={"id": 1}, headers={"existing": "header"}
        )
        await queue.publish("jobs", message)

    await asyncio.sleep(0.1)

    assert received_message is not None
    assert received_message.headers is not None
    assert "traceparent" in received_message.headers

    publish_span = tracer.spans[1]
    receive_span = tracer.spans[2]
    assert publish_span.name == "queue.publish jobs"
    assert receive_span.name == "queue.receive jobs"
    assert receive_span.parent_context is not None
    assert receive_span.context[0] == receive_span.parent_context[0]

    await queue.close()


@pytest.mark.asyncio
async def test_memory_queue_receive_span_parent_is_publish_span_not_ambient() -> None:
    """Memory queue receive span should be child of publish span, not ambient context.

    This test verifies the specific semantic that the consumer's receive span
    should link to the publish span, NOT to whatever span was active when
    publish() was called.

    Scenario:
    - Ambient span "test.workflow" is active
    - Inside it, we call queue.publish() which creates "queue.publish jobs"
    - The consumer receives the message and creates "queue.receive jobs"
    - The receive span MUST be a child of "queue.publish jobs", not "test.workflow"

    This proves that inject_context is called AFTER the publish span is started.
    """
    from lexigram.queue.backends.memory import InMemoryQueue

    tracer = FakeTracer()
    queue = InMemoryQueue()
    await queue.connect()
    queue.set_tracer(tracer)

    received_message = None

    async def handler(msg: BusMessage) -> None:
        nonlocal received_message
        received_message = msg

    await queue.subscribe("jobs", handler)

    # Create an ambient/upstream span
    ambient_span = tracer.start_span("test.workflow")
    with ambient_span:
        # Publish inside the ambient span
        message = BusMessage(topic="jobs", payload={"work": "data"})
        await queue.publish("jobs", message)

    # Wait for async delivery
    await asyncio.sleep(0.1)

    assert received_message is not None
    assert received_message.headers is not None
    assert "traceparent" in received_message.headers

    # Extract spans
    ambient = tracer.spans[0]
    publish = tracer.spans[1]
    receive = tracer.spans[2]

    assert ambient.name == "test.workflow"
    assert publish.name == "queue.publish jobs"
    assert receive.name == "queue.receive jobs"

    # Key assertion: receive span's parent should be the publish span
    # (receive.parent_context should match publish.context, NOT ambient.context)
    assert receive.parent_context is not None
    assert receive.parent_context == publish.context, (
        "Receive span should be child of publish span, not ambient span. "
        "This means inject_context was called before start_span(publish)."
    )

    await queue.close()


@pytest.mark.asyncio
async def test_redis_queue_receive_creates_span_with_context() -> None:
    """Redis queue should pass extracted context to start_span.

    This test simulates the receive path using a fake pubsub client that
    delivers messages with traceparent headers, proving that the context
    extraction and span creation code path works correctly.
    """
    from lexigram.queue.backends.redis import RedisQueue

    tracer = FakeTracer()

    fake_pubsub = MagicMock()
    fake_client = MagicMock()
    fake_client.pubsub.return_value = fake_pubsub

    queue = RedisQueue(url="redis://localhost:6379")
    queue._client = fake_client
    queue.set_tracer(tracer)

    parent_span = tracer.start_span("test.producer")
    trace_headers: dict[str, str] = {}
    tracer.inject_context(trace_headers)

    message_data = {
        "id": "msg-123",
        "topic": "jobs",
        "payload": {"task": "work"},
        "headers": trace_headers,
    }

    async def fake_listen() -> Any:
        yield {"type": "message", "data": json.dumps(message_data)}

    fake_pubsub.listen = fake_listen
    fake_pubsub.subscribe = AsyncMock()

    handler_called = False

    async def handler(msg: BusMessage) -> None:
        nonlocal handler_called
        handler_called = True

    await queue.subscribe("jobs", handler)

    await asyncio.sleep(0.1)

    assert handler_called
    assert len(tracer.spans) >= 2
    receive_span = tracer.spans[1]
    assert receive_span.name == "queue.receive jobs"
    assert receive_span.attributes["messaging.system"] == "redis"
    assert receive_span.parent_context is not None
    assert receive_span.context[0] == parent_span.context[0]


@pytest.mark.asyncio
async def test_rabbitmq_queue_receive_creates_span_with_context() -> None:
    """RabbitMQ queue should pass extracted context to start_span.

    This test simulates the receive path with a fake channel and message,
    proving context propagation works.
    """
    from lexigram.queue.backends.rabbitmq import RabbitMQQueue

    tracer = FakeTracer()

    fake_queue = MagicMock()
    fake_channel = MagicMock()
    fake_connection = MagicMock()

    async def fake_declare_queue(name: str, durable: bool = False) -> Any:
        return fake_queue

    fake_channel.declare_queue = fake_declare_queue

    queue = RabbitMQQueue(url="amqp://guest:guest@localhost/")
    queue._connection = fake_connection
    queue._channel = fake_channel
    queue.set_tracer(tracer)

    parent_span = tracer.start_span("test.producer")
    trace_headers: dict[str, str] = {}
    tracer.inject_context(trace_headers)

    message_data = {
        "id": "msg-456",
        "topic": "jobs",
        "payload": {"task": "execute"},
        "headers": trace_headers,
    }

    class FakeMessage:
        def __init__(self, body_bytes: bytes) -> None:
            self.body = body_bytes

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        def process(self) -> FakeMessage:
            return self

    fake_message = FakeMessage(json.dumps(message_data).encode())

    handler_invoked = False
    captured_handler = None

    async def fake_consume(handler_fn: Any) -> None:
        nonlocal captured_handler, handler_invoked
        captured_handler = handler_fn
        await handler_fn(fake_message)
        handler_invoked = True

    fake_queue.consume = fake_consume

    handler_called = False

    async def handler(msg: BusMessage) -> None:
        nonlocal handler_called
        handler_called = True

    await queue.subscribe("jobs", handler)

    await asyncio.sleep(0.1)

    assert handler_called
    assert handler_invoked
    assert len(tracer.spans) >= 2
    receive_span = tracer.spans[1]
    assert receive_span.name == "queue.receive jobs"
    assert receive_span.attributes["messaging.system"] == "rabbitmq"
    assert receive_span.parent_context is not None
    assert receive_span.context[0] == parent_span.context[0]


@pytest.mark.asyncio
async def test_memory_queue_publish_with_noop_tracer_does_not_raise() -> None:
    """Memory queue publish with NoOpTracer should not raise AttributeError.

    This is a regression test for the blocker where NoOpSpan doesn't expose
    a `context` attribute, causing publish to fail when attempting to call
    self._tracer.inject_context(trace_headers, context=span.context).
    """
    from lexigram.observability.core import NoOpTracer
    from lexigram.queue.backends.memory import InMemoryQueue

    tracer = NoOpTracer()
    queue = InMemoryQueue()
    queue.set_tracer(tracer)

    # This should not raise AttributeError: 'NoOpSpan' object has no attribute 'context'
    await queue.publish("jobs", BusMessage(topic="jobs", payload={"id": 1}))


__all__: list[str] = []
