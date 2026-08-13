"""Unit tests for the queue admin action handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.contracts.queue.types import BusMessage
from lexigram.queue.admin.actions import retry_failed
from lexigram.queue.core.dlq import DeadLetterQueue


class _ActionContainer:
    """Minimal container fake resolving the DLQ and queue backend."""

    def __init__(self, dlq: DeadLetterQueue | None, queue: object | None) -> None:
        self._dlq = dlq
        self._queue = queue

    async def resolve_optional(self, service_type: type[object]) -> object | None:
        if service_type is DeadLetterQueue:
            return self._dlq
        if service_type is QueueProtocol:
            return self._queue
        return None


@pytest.mark.asyncio
async def test_retry_failed_republishes_all_entries() -> None:
    """Drained DLQ entries are re-published to their original topics."""
    dlq = DeadLetterQueue()
    first = BusMessage(topic="orders", payload={"id": 1})
    second = BusMessage(topic="payments", payload={"id": 2})
    await dlq.push(first, "boom 1")
    await dlq.push(second, "boom 2")
    queue = MagicMock()
    queue.publish = AsyncMock()
    container = _ActionContainer(dlq, queue)

    result = await retry_failed(container)

    assert result["ok"] is True
    assert result["echo"] == {"retried": 2, "failed": 0}
    queue.publish.assert_any_await("orders", first)
    queue.publish.assert_any_await("payments", second)
    assert queue.publish.await_count == 2
    assert dlq.size == 0


@pytest.mark.asyncio
async def test_retry_failed_with_no_entries_is_noop() -> None:
    """An empty DLQ reports success without publishing anything."""
    dlq = DeadLetterQueue()
    queue = MagicMock()
    queue.publish = AsyncMock()
    container = _ActionContainer(dlq, queue)

    result = await retry_failed(container)

    assert result["ok"] is True
    assert result["echo"] == {"retried": 0, "failed": 0}
    queue.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_failed_without_dlq_returns_error() -> None:
    """A container without a registered DLQ yields an actionable error."""
    queue = MagicMock()
    queue.publish = AsyncMock()
    container = _ActionContainer(None, queue)

    result = await retry_failed(container)

    assert result["ok"] is False
    assert "dead letter queue" in result["message"]
    queue.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_failed_without_queue_backend_returns_error() -> None:
    """A container without a queue backend yields an actionable error."""
    dlq = DeadLetterQueue()
    container = _ActionContainer(dlq, None)

    result = await retry_failed(container)

    assert result["ok"] is False
    assert "queue backend" in result["message"]


@pytest.mark.asyncio
async def test_retry_failed_repushes_entries_whose_publish_fails() -> None:
    """Entries whose publish fails are pushed back into the DLQ, not lost."""
    dlq = DeadLetterQueue()
    good = BusMessage(topic="orders", payload={"id": 1})
    bad = BusMessage(topic="payments", payload={"id": 2})
    await dlq.push(good, "boom 1")
    await dlq.push(bad, "boom 2")
    queue = MagicMock()

    async def _publish(topic: str, message: BusMessage) -> None:
        if message is bad:
            raise ConnectionError("broker down")

    queue.publish = _publish
    container = _ActionContainer(dlq, queue)

    result = await retry_failed(container)

    assert result["ok"] is False
    assert result["echo"] == {"retried": 1, "failed": 1}
    assert dlq.size == 1
    repushed = await dlq.drain()
    assert repushed[0].message is bad


__all__ = [
    "test_retry_failed_republishes_all_entries",
    "test_retry_failed_repushes_entries_whose_publish_fails",
    "test_retry_failed_with_no_entries_is_noop",
    "test_retry_failed_without_dlq_returns_error",
    "test_retry_failed_without_queue_backend_returns_error",
]
