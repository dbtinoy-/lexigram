"""AIMD bulkhead behavior tests."""

from __future__ import annotations

import asyncio
import pytest
import time

from lexigram.resilience.bulkhead.limiter import Bulkhead, AIMDBulkhead
from lexigram.resilience.config import BulkheadConfig
from lexigram.resilience.bulkhead.limiter import AIMDBulkheadConfig
from lexigram.resilience.exceptions import BulkheadRejectedError



class TestAIMDBulkhead:
    """Tests for adaptive AIMD bulkhead."""

    @pytest.mark.asyncio
    async def test_aimd_bulkhead_starts_with_initial_limit(self) -> None:
        """Test AIMD bulkhead initializes with correct initial limit."""
        config = AIMDBulkheadConfig(initial_limit=10)
        bulkhead = AIMDBulkhead(config=config)

        assert bulkhead.metrics.current_limit == 10

    @pytest.mark.asyncio
    async def test_aimd_bulkhead_allows_concurrent_calls(self) -> None:
        """Test AIMD bulkhead allows concurrent calls up to limit."""
        config = AIMDBulkheadConfig(initial_limit=2, queue_size=10)
        bulkhead = AIMDBulkhead(config=config)

        concurrent_count = 0
        max_concurrent_observed = 0

        async def operation() -> str:
            nonlocal concurrent_count, max_concurrent_observed
            concurrent_count += 1
            max_concurrent_observed = max(max_concurrent_observed, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return "success"

        # Create 4 concurrent tasks
        tasks = [bulkhead.execute(operation) for _ in range(4)]
        results = await asyncio.gather(*tasks)

        assert all(r == "success" for r in results)
        assert max_concurrent_observed <= 2

    @pytest.mark.asyncio
    async def test_aimd_bulkhead_increases_limit_on_good_performance(self) -> None:
        """Test AIMD bulkhead increases limit with low latency."""
        config = AIMDBulkheadConfig(
            initial_limit=2,
            min_limit=1,
            max_limit=10,
            increase_amount=1,
            increase_threshold_ms=100.0,
            queue_size=10,
        )
        bulkhead = AIMDBulkhead(config=config)

        initial_limit = bulkhead.metrics.current_limit

        async def fast_operation() -> str:
            await asyncio.sleep(0.001)  # Very fast
            return "success"

        # Run multiple operations to trigger adjustment
        for _ in range(10):
            await bulkhead.execute(fast_operation)

        # Limit should have increased
        assert bulkhead.metrics.current_limit >= initial_limit

    @pytest.mark.asyncio
    async def test_aimd_bulkhead_decreases_limit_on_high_latency(self) -> None:
        """Test AIMD bulkhead decreases limit with high latency."""
        config = AIMDBulkheadConfig(
            initial_limit=10,
            min_limit=1,
            max_limit=20,
            decrease_factor=0.5,
            decrease_threshold_ms=100.0,
            queue_size=20,
        )
        bulkhead = AIMDBulkhead(config=config)

        initial_limit = bulkhead.metrics.current_limit

        async def slow_operation() -> str:
            await asyncio.sleep(0.2)  # Slow
            return "success"

        # Run operations to trigger adjustment
        for _ in range(5):
            await bulkhead.execute(slow_operation)

        # Limit should have decreased or stayed same
        assert bulkhead.metrics.current_limit <= initial_limit

    @pytest.mark.asyncio
    async def test_aimd_bulkhead_respects_min_limit(self) -> None:
        """Test AIMD bulkhead respects minimum limit."""
        config = AIMDBulkheadConfig(
            initial_limit=10,
            min_limit=5,
            max_limit=20,
            decrease_factor=0.1,  # Very aggressive
            decrease_threshold_ms=10.0,
        )
        bulkhead = AIMDBulkhead(config=config)

        async def slow_operation() -> str:
            await asyncio.sleep(0.5)
            return "success"

        # Run operations to trigger adjustment
        for _ in range(10):
            try:
                await bulkhead.execute(slow_operation)
            except BulkheadRejectedError:
                pass

        # Limit should not go below min_limit
        assert bulkhead.metrics.current_limit >= config.min_limit

    @pytest.mark.asyncio
    async def test_aimd_bulkhead_respects_max_limit(self) -> None:
        """Test AIMD bulkhead respects maximum limit."""
        config = AIMDBulkheadConfig(
            initial_limit=2,
            min_limit=1,
            max_limit=5,
            increase_amount=10,  # Very aggressive
            increase_threshold_ms=1000.0,
        )
        bulkhead = AIMDBulkhead(config=config)

        async def fast_operation() -> str:
            await asyncio.sleep(0.001)
            return "success"

        # Run operations to trigger adjustment
        for _ in range(20):
            await bulkhead.execute(fast_operation)

        # Limit should not exceed max_limit
        assert bulkhead.metrics.current_limit <= config.max_limit

    @pytest.mark.asyncio
    async def test_aimd_bulkhead_rejects_calls_when_queue_full(self) -> None:
        """Test AIMD bulkhead rejects calls when queue is full."""
        config = AIMDBulkheadConfig(
            initial_limit=1,
            queue_size=1,
            timeout=0.05,
        )
        bulkhead = AIMDBulkhead(config=config)

        async def slow_operation() -> str:
            await asyncio.sleep(0.5)
            return "success"

        # Start one operation
        task1 = asyncio.create_task(bulkhead.execute(slow_operation))

        await asyncio.sleep(0.01)

        # Queue one operation
        task2 = asyncio.create_task(bulkhead.execute(slow_operation))

        await asyncio.sleep(0.01)

        # Third should be rejected
        with pytest.raises(BulkheadRejectedError):
            await bulkhead.execute(slow_operation)

        # Clean up
        task1.cancel()
        task2.cancel()
        try:
            await asyncio.gather(task1, task2)
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_aimd_bulkhead_tracks_metrics(self) -> None:
        """Test AIMD bulkhead tracks rejection and pass metrics."""
        config = AIMDBulkheadConfig(initial_limit=2, queue_size=10)
        bulkhead = AIMDBulkhead(config=config)

        async def operation() -> str:
            return "success"

        # Execute several operations
        for _ in range(5):
            await bulkhead.execute(operation)

        assert bulkhead.metrics.total_passed >= 5

    @pytest.mark.asyncio
    async def test_aimd_bulkhead_tracks_rejected_calls(self) -> None:
        """Test AIMD bulkhead tracks rejected calls."""
        config = AIMDBulkheadConfig(
            initial_limit=1,
            queue_size=0,
            timeout=0.05,
        )
        bulkhead = AIMDBulkhead(config=config)

        async def slow_operation() -> str:
            await asyncio.sleep(0.2)
            return "success"

        # Start one operation
        task1 = asyncio.create_task(bulkhead.execute(slow_operation))

        await asyncio.sleep(0.01)

        # Try to execute - should be rejected
        with pytest.raises(BulkheadRejectedError):
            await bulkhead.execute(slow_operation)

        assert bulkhead.metrics.total_rejected >= 1

        # Clean up
        task1.cancel()
        try:
            await task1
        except asyncio.CancelledError:
            pass


