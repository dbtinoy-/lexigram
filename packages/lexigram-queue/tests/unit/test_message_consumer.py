"""Tests for MessageConsumer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.queue.types import BusMessage
from lexigram.queue.consumers.consumer import MessageConsumer


class ConcreteMessageConsumer(MessageConsumer):
    """Concrete implementation of MessageConsumer for testing."""

    topic = "test-topic"

    async def handle(self, message: BusMessage) -> None:
        """Handle a message."""
        self.last_message = message


class TestMessageConsumer:
    """Test MessageConsumer."""

    @pytest.fixture
    def mock_queue(self) -> MagicMock:
        """Create a mock queue."""
        queue = MagicMock()
        queue.subscribe = AsyncMock()
        return queue

    @pytest.mark.asyncio
    async def test_start_subscribes_to_topic(self, mock_queue: MagicMock) -> None:
        """start() should subscribe to the topic."""
        consumer = ConcreteMessageConsumer(mock_queue)
        await consumer.start()

        mock_queue.subscribe.assert_called_once()
        call_args = mock_queue.subscribe.call_args
        assert call_args[0][0] == "test-topic"

    @pytest.mark.asyncio
    async def test_handle_invoked_on_message(self, mock_queue: MagicMock) -> None:
        """handle() should be invoked when _dispatch() is called."""
        consumer = ConcreteMessageConsumer(mock_queue)
        await consumer.start()

        # Get the handler function passed to subscribe
        handler = mock_queue.subscribe.call_args[0][1]

        msg = BusMessage(topic="test-topic", payload="data")
        consumer.last_message = None
        await handler(msg)

        assert consumer.last_message == msg

    @pytest.mark.asyncio
    async def test_stop_ignores_messages(self, mock_queue: MagicMock) -> None:
        """After stop(), _dispatch() should not call handle()."""
        consumer = ConcreteMessageConsumer(mock_queue)
        await consumer.start()
        await consumer.stop()

        handler = mock_queue.subscribe.call_args[0][1]

        consumer.last_message = None
        msg = BusMessage(topic="test-topic", payload="data")
        await handler(msg)

        # Should not have called handle
        assert consumer.last_message is None

    @pytest.mark.asyncio
    async def test_handler_error_does_not_propagate(
        self, mock_queue: MagicMock
    ) -> None:
        """handle() raising should not propagate the exception."""
        consumer = ConcreteMessageConsumer(mock_queue)
        await consumer.start()

        # Override handle to raise
        async def failing_handle(message: BusMessage) -> None:
            raise ValueError("handler error")

        consumer.handle = failing_handle

        handler = mock_queue.subscribe.call_args[0][1]

        msg = BusMessage(topic="test-topic", payload="data")
        # Should not raise
        await handler(msg)


__all__ = ["TestMessageConsumer"]
