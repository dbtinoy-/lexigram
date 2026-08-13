"""Tests for RabbitMQQueue backend."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.queue.types import BusMessage


def _make_queue(**kwargs: Any) -> Any:
    from lexigram.queue.backends.rabbitmq import RabbitMQQueue

    return RabbitMQQueue(
        url="amqp://guest:guest@localhost/",
        exchange="lexigram",
        **kwargs,
    )


def _inject_clients(queue: Any, connection: MagicMock, channel: MagicMock) -> None:
    """Inject mock connection and channel directly into the queue."""
    queue._connection = connection
    queue._channel = channel


class TestRabbitMQQueue:
    """Unit tests for RabbitMQQueue."""

    @pytest.mark.asyncio
    async def test_publish_requires_connection(self) -> None:
        """publish() raises RuntimeError when not connected."""
        queue = _make_queue()
        msg = BusMessage(id="msg-1", topic="test-topic", payload={"key": "value"})

        with pytest.raises(RuntimeError, match="not connected"):
            await queue.publish("test-topic", msg)

    @pytest.mark.asyncio
    async def test_subscribe_requires_connection(self) -> None:
        """subscribe() raises RuntimeError when not connected."""
        queue = _make_queue()

        handler = AsyncMock()
        with pytest.raises(RuntimeError, match="not connected"):
            await queue.subscribe("test-topic", handler)

    @pytest.mark.asyncio
    async def test_set_tracer_accepts_none(self) -> None:
        """set_tracer() should accept None to clear tracer."""
        queue = _make_queue()
        queue.set_tracer(None)

        assert queue._tracer is None

    @pytest.mark.asyncio
    async def test_set_hook_registry_accepts_none(self) -> None:
        """set_hook_registry() should accept None to clear hooks."""
        queue = _make_queue()
        queue.set_hook_registry(None)

        assert queue._hooks is None

    @pytest.mark.asyncio
    async def test_close_with_no_connection(self) -> None:
        """close() should handle no connection gracefully."""
        queue = _make_queue()
        await queue.close()

        assert queue._connection is None
        assert queue._channel is None


__all__ = ["TestRabbitMQQueue"]