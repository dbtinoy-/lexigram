"""Tests for RedisQueue backend."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.queue.types import BusMessage


def _make_queue(**kwargs: Any) -> Any:
    from lexigram.queue.backends.redis import RedisQueue

    return RedisQueue(
        url="redis://localhost:6379/0",
        **kwargs,
    )


def _inject_client(queue: Any, client: MagicMock) -> None:
    """Inject a mock Redis client directly into the queue."""
    queue._client = client


class TestRedisQueue:
    """Unit tests for RedisQueue using dependency injection patterns."""

    @pytest.mark.asyncio
    async def test_publish_requires_connection(self) -> None:
        """publish() raises RuntimeError when not connected."""
        queue = _make_queue()
        msg = BusMessage(id="msg-1", topic="test-topic", payload={"key": "value"})

        with pytest.raises(RuntimeError, match="not connected"):
            await queue.publish("test-topic", msg)

    @pytest.mark.asyncio
    async def test_publish_serializes_and_publishes_message(self) -> None:
        """publish() should serialize and publish message to Redis."""
        queue = _make_queue()
        mock_client = AsyncMock()
        _inject_client(queue, mock_client)

        msg = BusMessage(id="msg-1", topic="test-topic", payload={"key": "value"})
        await queue.publish("test-topic", msg)

        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args
        assert call_args.args[0] == "test-topic"

        published = json.loads(call_args.args[1])
        assert published["id"] == "msg-1"
        assert published["topic"] == "test-topic"
        assert published["payload"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_publish_with_headers(self) -> None:
        """publish() should merge message headers with trace headers."""
        queue = _make_queue()
        mock_client = AsyncMock()
        _inject_client(queue, mock_client)

        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_span.context = MagicMock()
        mock_tracer.start_span = MagicMock(return_value=mock_span)
        mock_tracer.inject_context = MagicMock()
        queue._tracer = mock_tracer

        msg = BusMessage(
            id="msg-1",
            topic="test-topic",
            payload={"key": "value"},
            headers={"x-custom": "header-value"},
        )
        await queue.publish("test-topic", msg)

        mock_tracer.inject_context.assert_called_once()
        call_args = mock_client.publish.call_args
        published = json.loads(call_args.args[1])
        assert "x-custom" in published["headers"]

    @pytest.mark.asyncio
    async def test_subscribe_raises_when_not_connected(self) -> None:
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


__all__ = ["TestRedisQueue"]