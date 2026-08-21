"""Bulkhead concurrency-limit tests."""

from __future__ import annotations

import asyncio
import pytest
import time

from lexigram.resilience.bulkhead.limiter import Bulkhead, AIMDBulkhead
from lexigram.resilience.config import BulkheadConfig
from lexigram.resilience.bulkhead.limiter import AIMDBulkheadConfig
from lexigram.resilience.exceptions import BulkheadRejectedError



class TestBulkheadConcurrency:
    """Tests for bulkhead concurrency management."""

    @pytest.mark.asyncio
    async def test_bulkhead_concurrent_execution_limited(self) -> None:
        """Test bulkhead properly limits concurrent executions."""
        config = BulkheadConfig(name="test", max_concurrent=3, queue_size=10)
        bulkhead = Bulkhead(config=config)

        executed_times: list[tuple[float, float]] = []

        async def timed_operation(operation_id: int) -> int:
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.05)
            end = asyncio.get_event_loop().time()
            executed_times.append((start, end))
            return operation_id

        # Execute many operations concurrently
        tasks = [
            bulkhead.execute(timed_operation, i) for i in range(12)
        ]
        results = await asyncio.gather(*tasks)

        assert results == list(range(12))

        # Check that at most 3 operations ran concurrently
        # (this is approximate, checking the count at different time points)
        executed_times.sort()
        for i in range(len(executed_times)):
            concurrent = sum(
                1
                for start, end in executed_times
                if start <= executed_times[i][0] <= end
            )
            assert concurrent <= 3

    @pytest.mark.asyncio
    async def test_bulkhead_queue_management(self) -> None:
        """Test bulkhead queue management with many operations."""
        config = BulkheadConfig(name="test", max_concurrent=2, queue_size=5)
        bulkhead = Bulkhead(config=config)

        results = []

        async def operation(op_id: int) -> int:
            await asyncio.sleep(0.05)  # Increased sleep to allow rejection
            results.append(op_id)
            return op_id

        # Queue is full after max_concurrent + queue_size (7 total)
        tasks = []
        for i in range(7):
            task = asyncio.create_task(bulkhead.execute(operation, i))
            tasks.append(task)

        # Give tasks time to queue
        await asyncio.sleep(0.01)

        # 8th should be rejected (exceeds max_concurrent + queue_size)
        with pytest.raises(BulkheadRejectedError):
            await bulkhead.execute(operation, 7)

        # Wait for all to complete
        await asyncio.gather(*tasks)

        assert len(results) == 7
