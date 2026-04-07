"""Tests for core queue reliability components (pipeline, DLQ, outbox)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.queue.types import BusMessage
from lexigram.queue.core.dlq import DeadLetterEntry, DeadLetterQueue
from lexigram.queue.core.outbox import OutboxEntry, TransactionalOutbox
from lexigram.queue.core.pipeline import MessagePipeline, MiddlewareBase


class MockMiddleware(MiddlewareBase):
    """Mock middleware for testing."""

    def __init__(self) -> None:
        self.called = False
        self.message: BusMessage | None = None

    async def process(self, message: BusMessage, next_handler) -> None:  # noqa: ANN001
        self.called = True
        self.message = message
        await next_handler(message)


class TestMessagePipeline:
    """Test MessagePipeline middleware chain."""

    @pytest.mark.asyncio
    async def test_pipeline_calls_handler_with_no_middleware(self) -> None:
        """Empty pipeline should call terminal handler."""
        pipeline = MessagePipeline()
        handler = AsyncMock()
        msg = BusMessage(topic="test", payload="data")
        await pipeline.execute(msg, handler)
        handler.assert_called_once_with(msg)

    @pytest.mark.asyncio
    async def test_middleware_wraps_handler(self) -> None:
        """Middleware should wrap and call next handler."""
        pipeline = MessagePipeline()
        mw = MockMiddleware()
        pipeline.add(mw)

        handler = AsyncMock()
        msg = BusMessage(topic="test", payload="data")
        await pipeline.execute(msg, handler)

        assert mw.called
        assert mw.message == msg
        handler.assert_called_once_with(msg)

    @pytest.mark.asyncio
    async def test_multiple_middleware_in_order(self) -> None:
        """Multiple middleware should execute in order."""
        pipeline = MessagePipeline()
        mw1 = MockMiddleware()
        mw2 = MockMiddleware()
        pipeline.add(mw1)
        pipeline.add(mw2)

        handler = AsyncMock()
        msg = BusMessage(topic="test", payload="data")
        await pipeline.execute(msg, handler)

        assert mw1.called
        assert mw2.called
        assert mw1.message == msg
        assert mw2.message == msg
        handler.assert_called_once_with(msg)


class TestDeadLetterQueue:
    """Test DeadLetterQueue."""

    @pytest.mark.asyncio
    async def test_push_and_drain(self) -> None:
        """Push entries and drain the queue."""
        dlq = DeadLetterQueue()
        msg = BusMessage(topic="test", payload="data")
        await dlq.push(msg, "test error")

        assert dlq.size == 1

        entries = await dlq.drain()
        assert len(entries) == 1
        assert entries[0].message == msg
        assert entries[0].error == "test error"
        assert dlq.size == 0

    @pytest.mark.asyncio
    async def test_max_size_evicts_oldest(self) -> None:
        """When max_size exceeded, oldest entry is evicted."""
        dlq = DeadLetterQueue(max_size=2)

        msg1 = BusMessage(topic="topic1", payload="data1")
        msg2 = BusMessage(topic="topic2", payload="data2")
        msg3 = BusMessage(topic="topic3", payload="data3")

        await dlq.push(msg1, "error 1")
        await dlq.push(msg2, "error 2")
        await dlq.push(msg3, "error 3")

        assert dlq.size == 2

        entries = await dlq.drain()
        assert len(entries) == 2
        # msg1 should have been evicted
        assert entries[0].message == msg2
        assert entries[1].message == msg3

    @pytest.mark.asyncio
    async def test_drain_clears_queue(self) -> None:
        """Drain should clear the queue."""
        dlq = DeadLetterQueue()
        msg = BusMessage(topic="test", payload="data")
        await dlq.push(msg, "error")

        await dlq.drain()
        assert dlq.size == 0


class TestTransactionalOutbox:
    """Test TransactionalOutbox."""

    @pytest.mark.asyncio
    async def test_stage_and_flush(self) -> None:
        """Stage messages and flush them."""
        queue = AsyncMock()
        outbox = TransactionalOutbox(queue)

        msg = BusMessage(topic="test", payload="data")
        outbox.stage("test-topic", msg)

        await outbox.flush()
        queue.publish.assert_called_once_with("test-topic", msg)

    @pytest.mark.asyncio
    async def test_multiple_entries_flush(self) -> None:
        """Flush multiple staged entries."""
        queue = AsyncMock()
        outbox = TransactionalOutbox(queue)

        msg1 = BusMessage(topic="topic1", payload="data1")
        msg2 = BusMessage(topic="topic2", payload="data2")
        outbox.stage("topic1", msg1)
        outbox.stage("topic2", msg2)

        await outbox.flush()
        assert queue.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_flush_handles_exceptions(self) -> None:
        """Flush should handle publish failures gracefully."""
        queue = AsyncMock()
        queue.publish.side_effect = [Exception("publish failed"), None]
        outbox = TransactionalOutbox(queue)

        msg1 = BusMessage(topic="topic1", payload="data1")
        msg2 = BusMessage(topic="topic2", payload="data2")
        outbox.stage("topic1", msg1)
        outbox.stage("topic2", msg2)

        # Should not raise
        await outbox.flush()
        assert queue.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_removes_entries(self) -> None:
        """Clear should remove all entries."""
        queue = AsyncMock()
        outbox = TransactionalOutbox(queue)

        msg = BusMessage(topic="test", payload="data")
        outbox.stage("test", msg)
        assert len(outbox._entries) == 1

        outbox.clear()
        assert len(outbox._entries) == 0

    @pytest.mark.asyncio
    async def test_flush_only_unpublished(self) -> None:
        """Flush should only re-publish failed entries."""
        queue = AsyncMock()
        queue.publish.return_value = None
        outbox = TransactionalOutbox(queue)

        msg1 = BusMessage(topic="topic1", payload="data1")
        msg2 = BusMessage(topic="topic2", payload="data2")
        outbox.stage("topic1", msg1)
        outbox.stage("topic2", msg2)

        await outbox.flush()
        assert queue.publish.call_count == 2

        # Second flush should not republish (all marked published)
        await outbox.flush()
        assert queue.publish.call_count == 2


__all__ = ["TestDeadLetterQueue", "TestMessagePipeline", "TestTransactionalOutbox"]
