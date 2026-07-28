"""Tests for SQSQueue backend."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.queue.types import BusMessage


def _make_queue(**kwargs: Any) -> Any:
    from lexigram.queue.backends.sqs import SQSQueue

    return SQSQueue(
        region="us-east-1",
        queue_url="https://sqs.us-east-1.amazonaws.com/123456789/test-queue",
        **kwargs,
    )


class TestSQSQueue:
    """Unit tests for SQSQueue."""

    @pytest.mark.asyncio
    async def test_publish_requires_connection(self) -> None:
        """publish() raises RuntimeError when not connected."""
        queue = _make_queue()
        msg = BusMessage(id="msg-1", topic="test-topic", payload={"key": "value"})

        with pytest.raises(RuntimeError, match="not connected"):
            await queue.publish("test-topic", msg)

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

    @pytest.mark.asyncio
    async def test_close_with_no_client(self) -> None:
        """close() should handle no client gracefully."""
        queue = _make_queue()
        await queue.close()

        assert queue._client is None

    def test_constructor_defaults(self) -> None:
        """SQSQueue should have correct default values."""
        queue = _make_queue()

        assert queue._region == "us-east-1"
        assert queue._queue_url == "https://sqs.us-east-1.amazonaws.com/123456789/test-queue"
        assert queue._visibility_timeout == 30
        assert queue._max_in_flight == 100


__all__ = ["TestSQSQueue"]