"""End-to-end test: the queue admin retry_failed action re-publishes.

The action is invoked through ``QueueAdminContributor.execute_action`` —
the same dispatch path ``DashboardAssembler.execute_action`` uses — with
the real ``InMemoryQueue`` backend, proving a previously failed message
lands back on its original topic.
"""

from __future__ import annotations

import asyncio

import pytest

from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.contracts.queue.types import BusMessage
from lexigram.queue.admin.contributor import QueueAdminContributor
from lexigram.queue.backends.memory import InMemoryQueue
from lexigram.queue.core.dlq import DeadLetterQueue


class _RetryContainer:
    """Minimal container fake resolving the DLQ and the queue backend."""

    def __init__(self, dlq: DeadLetterQueue, queue: object) -> None:
        self._dlq = dlq
        self._queue = queue

    async def resolve(self, service_type: type[object]) -> object | None:
        return None

    async def resolve_optional(self, service_type: type[object]) -> object | None:
        if service_type is DeadLetterQueue:
            return self._dlq
        if service_type is QueueProtocol:
            return self._queue
        return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retry_failed_republishes_failed_message_via_dashboard_dispatch() -> None:
    """A previously failed message is re-published to its original topic."""
    dlq = DeadLetterQueue()
    failed = BusMessage(topic="orders", payload={"id": 42})
    await dlq.push(failed, "handler boom")

    received: list[BusMessage] = []
    queue = InMemoryQueue()
    await queue.connect()

    async def record(message: BusMessage) -> None:
        received.append(message)

    await queue.subscribe("orders", record)

    contributor = QueueAdminContributor()
    await contributor.on_admin_boot(_RetryContainer(dlq, queue))

    result = await contributor.execute_action("retry_failed", {})

    assert result["ok"] is True
    assert result["echo"] == {"retried": 1, "failed": 0}
    assert dlq.size == 0
    for _ in range(50):
        if received:
            break
        await asyncio.sleep(0.01)
    assert len(received) == 1
    assert received[0].id == failed.id
    assert received[0].payload == {"id": 42}


__all__ = ["test_retry_failed_republishes_failed_message_via_dashboard_dispatch"]
