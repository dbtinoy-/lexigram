"""Tests for worker-pool service wiring."""

from unittest.mock import AsyncMock, patch

import pytest

from lexigram.tasks.dlq.core import DeadLetterQueue
from lexigram.tasks.execution.pool import WorkerPool
from lexigram.tasks.execution.worker import TaskWorker


@pytest.mark.asyncio
async def test_worker_pool_injects_default_dead_letter_queue() -> None:
    """WorkerPool should give each worker a DLQ instead of the re-enqueue fallback."""

    queue = AsyncMock()
    pool = WorkerPool(queue, handler_registry={}, size=1)

    with patch.object(TaskWorker, "start", new=AsyncMock()):
        await pool.start()

    assert isinstance(pool.workers[0].dlq, DeadLetterQueue)
