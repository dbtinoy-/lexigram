"""
Tests for Bulk Operations - Batch processing functionality.
"""

import asyncio
import contextlib
import time

import pytest

from lexigram.workflow.config import BulkOperationConfig
from lexigram.workflow.bulk import (
    BulkOperation,
    BulkOperationError,
    BulkOperationState,
    BulkOperationTimeoutError,
    bulk_filter,
    bulk_map,
    bulk_reduce,
)


class TestBulkOperationConfig:
    """Test bulk operation configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BulkOperationConfig()

        assert config.batch_size == 10
        assert config.max_concurrency == 5
        assert config.timeout == 300.0
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0
        assert config.circuit_breaker_config is None
        assert config.enable_progress_tracking is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = BulkOperationConfig(
            batch_size=20,
            max_concurrency=10,
            timeout=600.0,
            retry_attempts=5,
            retry_delay=2.0,
            enable_progress_tracking=False,
        )

        assert config.batch_size == 20
        assert config.max_concurrency == 10
        assert config.timeout == 600.0
        assert config.retry_attempts == 5
        assert config.retry_delay == 2.0
        assert config.enable_progress_tracking is False

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = BulkOperationConfig(batch_size=1, max_concurrency=1)
        assert config.batch_size == 1
        assert config.max_concurrency == 1

        # Invalid batch_size
        with pytest.raises(Exception):
            BulkOperationConfig(batch_size=0)

        # Invalid max_concurrency
        with pytest.raises(Exception):
            BulkOperationConfig(max_concurrency=0)

        # Very large max_concurrency is allowed; ensure it's accepted
        config = BulkOperationConfig(max_concurrency=101)
        assert config.max_concurrency == 101


@pytest.mark.asyncio
class TestBulkOperation:
    """Test bulk operation functionality."""

    async def test_initial_state(self):
        """Test initial bulk operation state."""
        operation = BulkOperation()
        assert operation.state == BulkOperationState.PENDING
        assert operation.metrics.total_items == 0
        assert operation.metrics.processed_items == 0

    async def test_successful_batch_processing(self):
        """Test successful batch processing."""

        async def processor(batch):
            # Simulate processing: double each number
            return [x * 2 for x in batch]

        operation = BulkOperation(BulkOperationConfig(batch_size=3))
        items = [1, 2, 3, 4, 5, 6, 7]

        results = []
        async for batch_result in operation.execute(items, processor):
            results.append(batch_result)

        assert len(results) == 3  # 7 items in batches of 3 = 3 batches (3, 3, 1)
        assert results[0].results == [2, 4, 6]  # First batch: [1,2,3] -> [2,4,6]
        assert results[1].results == [8, 10, 12]  # Second batch: [4,5,6] -> [8,10,12]
        assert results[2].results == [14]  # Third batch: [7] -> [14]

        assert operation.state == BulkOperationState.COMPLETED
        assert operation.metrics.total_items == 7
        assert operation.metrics.processed_items == 7
        assert operation.metrics.successful_items == 7
        assert operation.metrics.failed_items == 0
        assert operation.metrics.total_batches == 3
        assert operation.metrics.completed_batches == 3
        assert operation.metrics.failed_batches == 0

    async def test_batch_with_failures(self):
        """Test batch processing with some failures."""

        async def processor(batch):
            results = []
            for x in batch:
                if x == 5:  # Fail only on item 5
                    raise ValueError(f"Failed on {x}")
                results.append(x * 2)
            return results

        operation = BulkOperation(
            BulkOperationConfig(
                batch_size=3,
                retry_attempts=0,  # No retries for this test
            ),
        )
        items = [1, 2, 3, 4, 5, 6, 7, 8, 9]

        results = []
        async for batch_result in operation.execute(items, processor):
            results.append(batch_result)

        # Check that batches with failures are recorded
        failed_batches = list(filter(lambda r: r.errors, results))
        successful_batches = list(filter(lambda r: not r.errors, results))

        assert len(failed_batches) > 0
        assert len(successful_batches) > 0

        # Check metrics
        assert operation.metrics.failed_items > 0
        assert operation.metrics.successful_items > 0
        assert operation.metrics.failed_batches > 0

    async def test_retry_mechanism(self):
        """Test retry mechanism for failed batches."""
        call_count = 0

        async def processor(batch):
            nonlocal call_count
            call_count += 1

            # Fail on first two attempts, succeed on third
            if call_count < 3:
                raise ValueError("Temporary failure")
            return [x * 2 for x in batch]

        operation = BulkOperation(
            BulkOperationConfig(
                batch_size=2,
                retry_attempts=2,
                retry_delay=0.01,  # Fast retry for testing
            ),
        )
        items = [1, 2]

        results = []
        async for batch_result in operation.execute(items, processor):
            results.append(batch_result)

        assert len(results) == 1
        assert results[0].results == [2, 4]  # Should succeed after retries
        assert results[0].retry_count == 2
        assert operation.metrics.total_retries == 2

    async def test_concurrency_control(self):
        """Test concurrency control with semaphore."""

        async def processor(batch):
            # Simulate variable processing time
            await asyncio.sleep(len(batch) * 0.01)
            return [x * 2 for x in batch]

        operation = BulkOperation(
            BulkOperationConfig(
                batch_size=2,
                max_concurrency=2,  # Only 2 concurrent batches
            ),
        )
        items = [1, 2, 3, 4, 5, 6, 7, 8]  # 4 batches

        start_time = time.time()
        results = []
        async for batch_result in operation.execute(items, processor):
            results.append(batch_result)

        duration = time.time() - start_time

        # With concurrency=2 and batch processing time based on size,
        # the total time should be reasonable
        assert duration < 1.0  # Should complete relatively quickly
        assert len(results) == 4

    async def test_timeout_handling(self):
        """Test timeout handling."""

        async def slow_processor(batch):
            await asyncio.sleep(2.0)  # Longer than timeout
            return [x * 2 for x in batch]

        operation = BulkOperation(
            BulkOperationConfig(batch_size=2, timeout=0.1),  # Very short timeout
        )
        items = [1, 2]

        with pytest.raises(BulkOperationTimeoutError):
            async for _ in operation.execute(items, slow_processor):
                pass

    async def test_cancellation(self):
        """Test operation cancellation."""

        async def slow_processor(batch):
            await asyncio.sleep(1.0)
            return [x * 2 for x in batch]

        operation = BulkOperation(BulkOperationConfig(batch_size=2))
        items = [1, 2, 3, 4]

        # Start the operation
        task = asyncio.create_task(
            self._collect_results(operation, items, slow_processor),
        )

        # Cancel after a short delay
        await asyncio.sleep(0.1)
        await operation.cancel()

        # Wait for the task to complete or be cancelled
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except TimeoutError:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        # The operation may complete partially or be cancelled
        # We just check that cancel was called and the operation state is updated
        assert operation._cancelled is True

    async def _collect_results(self, operation, items, processor):
        """Helper to collect results for cancellation test."""
        async for _ in operation.execute(items, processor):
            pass

    async def test_progress_callbacks(self):
        """Test progress tracking callbacks."""
        progress_calls = []

        async def progress_callback(metrics):
            progress_calls.append(
                {
                    "processed": metrics.processed_items,
                    "total": metrics.total_items,
                    "success_rate": metrics.success_rate,
                },
            )

        async def processor(batch):
            return [x * 2 for x in batch]

        operation = BulkOperation(BulkOperationConfig(batch_size=2))
        operation.add_progress_callback(progress_callback)

        items = [1, 2, 3, 4]
        results = []
        async for batch_result in operation.execute(items, processor):
            results.append(batch_result)

        assert len(progress_calls) > 0
        assert progress_calls[-1]["processed"] == 4
        assert progress_calls[-1]["total"] == 4
        assert progress_calls[-1]["success_rate"] == 100.0

    async def test_empty_items(self):
        """Test handling of empty item list."""

        async def processor(batch):
            return [x * 2 for x in batch]

        operation = BulkOperation()
        items = []

        results = []
        async for batch_result in operation.execute(items, processor):
            results.append(batch_result)

        assert len(results) == 0
        assert operation.metrics.total_items == 0
        assert operation.state == BulkOperationState.COMPLETED

    async def test_no_processor_error(self):
        """Test error when no processor is provided."""
        operation = BulkOperation()
        items = [1, 2, 3]

        with pytest.raises(BulkOperationError, match="No processor function provided"):
            async for _ in operation.execute(items):
                pass


@pytest.mark.asyncio
class TestBulkOperationMetrics:
    """Test bulk operation metrics."""

    async def test_metrics_calculation(self):
        """Test metrics calculation."""

        async def processor(batch):
            # Simulate some failures
            results = []
            for x in batch:
                if x == 5:  # Fail on item 5
                    raise ValueError(f"Failed on {x}")
                results.append(x * 2)
            return results

        operation = BulkOperation(BulkOperationConfig(batch_size=2))
        items = [1, 2, 3, 4, 5, 6]

        async for _ in operation.execute(items, processor):
            pass

        metrics = operation.metrics
        assert metrics.total_items == 6
        assert metrics.processed_items == 6
        assert (
            metrics.successful_items == 4
        )  # 4 succeeded, 1 failed (item 5 fails, item 6 not processed due to batch failure)
        assert metrics.failed_items == 1
        assert metrics.success_rate == (4 / 6) * 100  # 4 succeeded out of 6 total
        assert metrics.total_batches == 3
        assert metrics.start_time is not None
        assert metrics.end_time is not None
        assert metrics.duration is not None
        assert metrics.duration > 0

    async def test_throughput_calculation(self):
        """Test throughput calculation."""

        async def processor(batch):
            await asyncio.sleep(0.01)  # Small delay
            return [x * 2 for x in batch]

        operation = BulkOperation(BulkOperationConfig(batch_size=5))
        items = list(range(50))  # 10 batches

        async for _ in operation.execute(items, processor):
            pass

        metrics = operation.metrics
        assert metrics.throughput > 0
        assert metrics.average_batch_time > 0


@pytest.mark.asyncio
class TestBulkUtilityFunctions:
    """Test bulk utility functions."""

    async def test_bulk_map(self):
        """Test bulk_map utility function."""

        def double(x):
            return x * 2

        items = [1, 2, 3, 4, 5, 6]
        results = await bulk_map(double, items, BulkOperationConfig(batch_size=3))

        assert results == [2, 4, 6, 8, 10, 12]

    async def test_bulk_filter(self):
        """Test bulk_filter utility function."""

        async def is_even(x):
            return x % 2 == 0

        items = [1, 2, 3, 4, 5, 6, 7, 8]
        results = []

        async for batch_result in bulk_filter(
            items,
            is_even,
            BulkOperationConfig(batch_size=3),
        ):
            results.extend(batch_result.results)

        assert results == [2, 4, 6, 8]

    async def test_bulk_reduce(self):
        """Test bulk_reduce utility function."""

        async def add(acc, x):
            return acc + x

        items = [1, 2, 3, 4, 5]
        await bulk_reduce(items, add, 0, BulkOperationConfig(batch_size=2))
