"""Bulkhead basic, arguments, and sync variants."""

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


