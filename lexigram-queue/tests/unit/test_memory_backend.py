"""Tests for InMemoryQueue backend."""
from __future__ import annotations

import asyncio

import pytest

from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.queue.types import BusMessage
from lexigram.queue.backends.memory import InMemoryQueue


class TestInMemoryQueue:
    """Test InMemoryQueue backend."""

    @pytest.fixture
    async def queue(self) -> InMemoryQueue:
        """Create and connect a queue for testing."""
        q = InMemoryQueue()
        await q.connect()
        yield q
        await q.close()

    @pytest.mark.asyncio
    async def test_connect_and_health_check(self) -> None:
        """Test connection and health check."""
        queue = InMemoryQueue()
        await queue.connect()
        result = await queue.health_check()
        assert result.status == HealthStatus.HEALTHY
        await queue.close()

    @pytest.mark.asyncio
    async def test_health_check_when_closed(self) -> None:
        """Test health check returns UNHEALTHY when closed."""
        queue = InMemoryQueue()
        result = await queue.health_check()
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self, queue: InMemoryQueue) -> None:
        """Test publish and subscribe."""
        received: list[BusMessage] = []

        async def handler(msg: BusMessage) -> None:
            received.append(msg)

        await queue.subscribe("test-topic", handler)
        msg = BusMessage(topic="test-topic", payload={"key": "value"})
        await queue.publish("test-topic", msg)
        await asyncio.sleep(0.01)
        assert len(received) == 1
        assert received[0].topic == "test-topic"
        assert received[0].payload == {"key": "value"}

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_topic(
        self, queue: InMemoryQueue
    ) -> None:
        """Test multiple subscribers on same topic."""
        received_a: list[BusMessage] = []
        received_b: list[BusMessage] = []

        async def handler_a(msg: BusMessage) -> None:
            received_a.append(msg)

        async def handler_b(msg: BusMessage) -> None:
            received_b.append(msg)

        await queue.subscribe("shared", handler_a)
        await queue.subscribe("shared", handler_b)
        msg = BusMessage(topic="shared", payload="hello")
        await queue.publish("shared", msg)
        await asyncio.sleep(0.01)
        assert len(received_a) == 1
        assert len(received_b) == 1
        assert received_a[0].payload == "hello"
        assert received_b[0].payload == "hello"

    @pytest.mark.asyncio
    async def test_topic_isolation(self, queue: InMemoryQueue) -> None:
        """Test that subscribers only receive from subscribed topics."""
        received_a: list[BusMessage] = []
        received_b: list[BusMessage] = []

        async def handler_a(msg: BusMessage) -> None:
            received_a.append(msg)

        async def handler_b(msg: BusMessage) -> None:
            received_b.append(msg)

        await queue.subscribe("topic-a", handler_a)
        await queue.subscribe("topic-b", handler_b)

        await queue.publish("topic-a", BusMessage(topic="topic-a", payload="msg-a"))
        await queue.publish("topic-b", BusMessage(topic="topic-b", payload="msg-b"))
        await asyncio.sleep(0.01)

        assert len(received_a) == 1
        assert len(received_b) == 1
        assert received_a[0].payload == "msg-a"
        assert received_b[0].payload == "msg-b"

    @pytest.mark.asyncio
    async def test_close_clears_state(self, queue: InMemoryQueue) -> None:
        """Test that close clears subscribers and marks as unhealthy."""
        received: list[BusMessage] = []

        async def handler(msg: BusMessage) -> None:
            received.append(msg)

        await queue.subscribe("topic", handler)
        await queue.close()
        result = await queue.health_check()
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_reconnect_after_close(self) -> None:
        """Test reconnecting after close."""
        queue = InMemoryQueue()
        await queue.connect()
        result1 = await queue.health_check()
        assert result1.status == HealthStatus.HEALTHY

        await queue.close()
        result2 = await queue.health_check()
        assert result2.status == HealthStatus.UNHEALTHY

        await queue.connect()
        result3 = await queue.health_check()
        assert result3.status == HealthStatus.HEALTHY
        await queue.close()

    @pytest.mark.asyncio
    async def test_multiple_messages_same_subscriber(self, queue: InMemoryQueue) -> None:
        """Test subscriber receives multiple messages."""
        received: list[BusMessage] = []

        async def handler(msg: BusMessage) -> None:
            received.append(msg)

        await queue.subscribe("topic", handler)
        for i in range(5):
            await queue.publish("topic", BusMessage(topic="topic", payload=i))

        await asyncio.sleep(0.05)
        assert len(received) == 5
        for i, msg in enumerate(received):
            assert msg.payload == i

    @pytest.mark.asyncio
    async def test_health_check_with_timeout(self, queue: InMemoryQueue) -> None:
        """Test health check with timeout parameter."""
        result = await queue.health_check(timeout=2.0)
        assert result.status == HealthStatus.HEALTHY


__all__ = []
