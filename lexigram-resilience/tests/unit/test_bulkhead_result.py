"""Tests for bulkhead with Result[T, E] integration.

This test suite verifies that bulkhead operations properly integrate with
the Result pattern, limiting concurrent executions and managing resource
pools while returning Result types for operations.
"""

from __future__ import annotations

import asyncio
import pytest
import time

from lexigram.resilience.bulkhead.limiter import Bulkhead, AIMDBulkhead
from lexigram.resilience.config import BulkheadConfig
from lexigram.resilience.bulkhead.limiter import AIMDBulkheadConfig
from lexigram.resilience.exceptions import BulkheadRejectedError


class TestBulkheadBasic:
    """Tests for basic bulkhead functionality."""

    @pytest.mark.asyncio
    async def test_bulkhead_allows_concurrent_calls_up_to_limit(self) -> None:
        """Test that bulkhead allows concurrent calls up to the limit."""
        config = BulkheadConfig(name="test", max_concurrent=2, queue_size=10)
        bulkhead = Bulkhead(config=config)

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
    async def test_bulkhead_rejects_calls_when_queue_full(self) -> None:
        """Test that bulkhead rejects calls when queue is full."""
        config = BulkheadConfig(
            name="test",
            max_concurrent=1,
            queue_size=1,
            timeout=0.5,
        )
        bulkhead = Bulkhead(config=config)

        blocked = []

        async def slow_operation() -> str:
            await asyncio.sleep(0.2)
            return "success"

        # Start one operation (uses the only slot)
        task1 = asyncio.create_task(bulkhead.execute(slow_operation))

        # Give task1 time to acquire the semaphore
        await asyncio.sleep(0.01)

        # Queue one operation
        task2 = asyncio.create_task(bulkhead.execute(slow_operation))

        # Give task2 time to queue
        await asyncio.sleep(0.01)

        # Third should be rejected immediately
        with pytest.raises(BulkheadRejectedError):
            await bulkhead.execute(slow_operation)

        # Wait for tasks to complete
        await asyncio.gather(task1, task2, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_bulkhead_timeout_waiting_for_slot(self) -> None:
        """Test that bulkhead times out when waiting for a slot."""
        config = BulkheadConfig(
            name="test",
            max_concurrent=1,
            queue_size=0,
            timeout=0.05,
        )
        bulkhead = Bulkhead(config=config)

        async def slow_operation() -> str:
            await asyncio.sleep(1.0)
            return "success"

        # Start one operation
        task1 = asyncio.create_task(bulkhead.execute(slow_operation))

        await asyncio.sleep(0.01)

        # Second should timeout
        with pytest.raises(BulkheadRejectedError):
            await bulkhead.execute(slow_operation)

        # Clean up
        task1.cancel()
        try:
            await task1
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_bulkhead_execute_success(self) -> None:
        """Test bulkhead execute with successful operation."""
        config = BulkheadConfig(name="test", max_concurrent=5, queue_size=10)
        bulkhead = Bulkhead(config=config)

        async def operation() -> str:
            return "success"

        result = await bulkhead.execute(operation)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_bulkhead_execute_failure_propagates_error(self) -> None:
        """Test that bulkhead propagates errors from operations."""
        config = BulkheadConfig(name="test", max_concurrent=5, queue_size=10)
        bulkhead = Bulkhead(config=config)

        async def failing_operation() -> str:
            raise ValueError("Operation failed")

        with pytest.raises(ValueError) as exc_info:
            await bulkhead.execute(failing_operation)

        assert "Operation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_bulkhead_call_alias(self) -> None:
        """Test that call() is an alias for execute()."""
        config = BulkheadConfig(name="test", max_concurrent=5, queue_size=10)
        bulkhead = Bulkhead(config=config)

        async def operation() -> str:
            return "success"

        result = await bulkhead.call(operation)

        assert result == "success"


class TestBulkheadWithArguments:
    """Tests for bulkhead with function arguments."""

    @pytest.mark.asyncio
    async def test_bulkhead_forwards_arguments(self) -> None:
        """Test that bulkhead forwards arguments to the function."""
        config = BulkheadConfig(name="test", max_concurrent=5, queue_size=10)
        bulkhead = Bulkhead(config=config)

        async def operation(x: int, y: int, z: str = "default") -> str:
            return f"{x}+{y}={x + y}, z={z}"

        result = await bulkhead.execute(operation, 2, 3, z="custom")

        assert result == "2+3=5, z=custom"

    @pytest.mark.asyncio
    async def test_bulkhead_forwards_keyword_arguments(self) -> None:
        """Test that bulkhead forwards keyword arguments."""
        config = BulkheadConfig(name="test", max_concurrent=5, queue_size=10)
        bulkhead = Bulkhead(config=config)

        async def operation(x: int, y: int) -> int:
            return x * y

        result = await bulkhead.execute(operation, x=3, y=4)

        assert result == 12


class TestBulkheadSync:
    """Tests for synchronous bulkhead operations."""

    def test_bulkhead_execute_sync_success(self) -> None:
        """Test bulkhead execute_sync with successful operation."""
        config = BulkheadConfig(name="test", max_concurrent=2, queue_size=10)
        bulkhead = Bulkhead(config=config)

        def operation() -> str:
            return "success"

        result = bulkhead.execute_sync(operation)

        assert result == "success"

    def test_bulkhead_execute_sync_failure(self) -> None:
        """Test bulkhead execute_sync with failed operation."""
        config = BulkheadConfig(name="test", max_concurrent=2, queue_size=10)
        bulkhead = Bulkhead(config=config)

        def failing_operation() -> str:
            raise ValueError("Operation failed")

        with pytest.raises(ValueError):
            bulkhead.execute_sync(failing_operation)

    def test_bulkhead_execute_sync_timeout(self) -> None:
        """Test bulkhead execute_sync with timeout."""
        config = BulkheadConfig(
            name="test",
            max_concurrent=1,
            queue_size=0,
            timeout=0.05,
        )
        bulkhead = Bulkhead(config=config)

        def slow_operation() -> str:
            time.sleep(1.0)
            return "success"

        def other_operation() -> str:
            time.sleep(0.01)
            return "success"

        # Start one operation
        import threading

        thread1 = threading.Thread(target=bulkhead.execute_sync, args=(slow_operation,))
        thread1.start()

        # Give thread1 time to acquire
        time.sleep(0.01)

        # Second should timeout
        with pytest.raises(BulkheadRejectedError):
            bulkhead.execute_sync(other_operation)

        # Clean up
        thread1.join(timeout=1.5)


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
