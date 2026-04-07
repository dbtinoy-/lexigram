"""Comprehensive tests for task components."""
import asyncio

import pytest

from lexigram.tasks import (
    JobProtocol,
    Priority,
    TaskExecutionError,
)
from lexigram.testing.clients.tasks import (
    MockTaskExecutor,
    MockTaskQueue,
    TaskTestBed,
    TaskTestClient,
)


class TestMockTaskQueue:
    """Test MockTaskQueue functionality."""

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        """Test basic enqueue/dequeue operations."""
        queue = MockTaskQueue()
        task = JobProtocol(
            id="test_task",
            name="test_task",
            args=("arg1",),
            kwargs={},
            priority=Priority.NORMAL,
        )

        # Enqueue task
        enqueue_result = await queue.enqueue(task)
        assert enqueue_result.is_ok()
        task_id = enqueue_result.unwrap()
        assert task_id == "test_task"

        # Dequeue task
        dequeued = await queue.dequeue()
        assert dequeued is not None
        assert dequeued.id == "test_task"

        # Queue should be empty
        empty_dequeue = await queue.dequeue()
        assert empty_dequeue is None

    @pytest.mark.asyncio
    async def test_get_task(self):
        """Test getting a task by ID."""
        queue = MockTaskQueue()
        task = JobProtocol(
            id="test_task",
            name="test_task",
            args=("arg1",),
            kwargs={},
            priority=Priority.NORMAL,
        )

        await queue.enqueue(task)
        retrieved = await queue.get_task("test_task")
        assert retrieved is not None
        assert retrieved.id == "test_task"

        # Non-existent task
        not_found = await queue.get_task("nonexistent")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test task cancellation."""
        queue = MockTaskQueue()
        task = JobProtocol(
            id="test_task",
            name="test_task",
            args=("arg1",),
            kwargs={},
            priority=Priority.NORMAL,
        )

        await queue.enqueue(task)
        cancelled = await queue.cancel_task("test_task")
        assert cancelled

        # Task should be gone
        retrieved = await queue.get_task("test_task")
        assert retrieved is None

        # Cancel non-existent task
        not_cancelled = await queue.cancel_task("nonexistent")
        assert not not_cancelled

    @pytest.mark.asyncio
    async def test_queue_stats(self):
        """Test queue statistics."""
        queue = MockTaskQueue()

        # Initially empty
        stats = await queue.get_queue_stats()
        assert stats["queued"] == 0
        assert stats["completed"] == 0

        # Add some tasks
        for i in range(3):
            task = JobProtocol(
                id=f"task_{i}",
                name=f"task_{i}",
                args=(f"arg{i}",),
                kwargs={},
                priority=Priority.NORMAL,
            )
            await queue.enqueue(task)

        stats = await queue.get_queue_stats()
        assert stats["queued"] == 3

        # Process one task
        await queue.dequeue()
        stats = await queue.get_queue_stats()
        assert stats["queued"] == 2
        assert stats["completed"] == 1

    @pytest.mark.asyncio
    async def test_clear_queue(self):
        """Test queue clearing."""
        queue = MockTaskQueue()

        # Add tasks
        for i in range(3):
            task = JobProtocol(
                id=f"task_{i}",
                name=f"task_{i}",
                args=(f"arg{i}",),
                kwargs={},
                priority=Priority.NORMAL,
            )
            await queue.enqueue(task)

        # Clear queue
        await queue.clear_queue()
        stats = await queue.get_queue_stats()
        assert stats["queued"] == 0


class TestMockTaskExecutor:
    """Test MockTaskExecutor functionality."""

    @pytest.mark.asyncio
    async def test_execute_email_task(self):
        """Test executing email notification task."""
        executor = MockTaskExecutor()
        task = JobProtocol(
            id="email_task",
            name="email_notification",
            args=("user@example.com", "Hello!"),
            kwargs={},
            priority=Priority.NORMAL,
        )

        result = await executor.execute_task(task)
        assert result.success
        assert result.value["task_id"] == "email_task"
        assert result.value["sent"] is True

    @pytest.mark.asyncio
    async def test_execute_data_processing_task(self):
        """Test executing data processing task."""
        executor = MockTaskExecutor()
        task = JobProtocol(
            id="data_task",
            name="data_processing",
            args=([10, 20, 30],),
            kwargs={"operation": "sum"},
            priority=Priority.NORMAL,
        )

        result = await executor.execute_task(task)
        assert result.success
        assert result.value["task_id"] == "data_task"
        assert result.value["result"] == 60  # sum of [10, 20, 30]

    @pytest.mark.asyncio
    async def test_execute_cleanup_task(self):
        """Test executing cleanup task."""
        executor = MockTaskExecutor()
        task = JobProtocol(
            id="cleanup_task",
            name="cleanup_job",
            args=(),
            kwargs={"target": "temp_files"},
            priority=Priority.NORMAL,
        )

        result = await executor.execute_task(task)
        assert result.success
        assert result.value["task_id"] == "cleanup_task"
        assert result.value["cleaned"] is True

    @pytest.mark.asyncio
    async def test_execution_stats(self):
        """Test execution statistics."""
        executor = MockTaskExecutor()

        # Initially empty
        stats = await executor.get_execution_stats()
        assert stats["executed"] == 0

        # Execute some tasks
        tasks = [
            JobProtocol(
                id="t1",
                name="email_notification",
                args=("a@b.com",),
                kwargs={},
                priority=Priority.NORMAL,
            ),
            JobProtocol(
                id="t2",
                name="data_processing",
                args=([1, 2],),
                kwargs={},
                priority=Priority.NORMAL,
            ),
            JobProtocol(
                id="t3",
                name="cleanup_job",
                args=(),
                kwargs={},
                priority=Priority.NORMAL,
            ),
        ]

        for task in tasks:
            await executor.execute_task(task)

        stats = await executor.get_execution_stats()
        assert stats["executed"] == 3
        assert stats["successful"] == 3
        assert stats["failed"] == 0


class TestTaskTestBedIntegration:
    """Test TaskTestBed integration functionality."""

    @pytest.mark.skip(reason="Async fixture compatibility issues with pytest 9")
    @pytest.mark.asyncio
    async def test_simulate_task_enqueue(self, task_test_bed: TaskTestBed):
        """Test simulating task enqueue."""
        task = JobProtocol(
            id="sim_task",
            name="sim_task",
            args=("arg",),
            kwargs={},
            priority=Priority.NORMAL,
        )

        await task_test_bed.simulate_task_enqueue(task)

        # Check mock queue
        retrieved = await task_test_bed.mock_queue.get_task("sim_task")
        assert retrieved is not None
        assert retrieved.name == "sim_task"

        # Check enqueued tasks
        enqueued = task_test_bed.get_enqueued_tasks()
        assert len(enqueued) == 1

    @pytest.mark.skip(reason="Async fixture compatibility issues with pytest 9")
    @pytest.mark.asyncio
    async def test_simulate_task_execution(self, task_test_bed: TaskTestBed):
        """Test simulating task execution."""
        task = JobProtocol(
            id="exec_task",
            name="email_notification",
            args=("test@example.com", "Test"),
            kwargs={},
            priority=Priority.NORMAL,
        )

        result = await task_test_bed.simulate_task_execution(task)

        # Check result
        assert result.success
        assert result.value["task_id"] == "exec_task"
        assert result.value["sent"] is True

        # Check executed tasks
        executed = task_test_bed.get_executed_tasks()
        assert len(executed) == 1
        assert executed[0]["task"].id == "exec_task"


class TestTaskTestClientIntegration:
    """Test TaskTestClient integration functionality."""

    @pytest.mark.skip(reason="Async fixture compatibility issues with pytest 9")
    @pytest.mark.asyncio
    async def test_create_worker_pool(self, task_test_client: TaskTestClient):
        """Test creating worker pool."""
        worker_pool = await task_test_client.create_worker_pool(num_workers=3)
        assert worker_pool is not None
        assert task_test_client.worker_pool is worker_pool

        await worker_pool.stop()

    @pytest.mark.skip(reason="Async fixture compatibility issues with pytest 9")
    @pytest.mark.asyncio
    async def test_create_scheduler(self, task_test_client: TaskTestClient):
        """Test creating task scheduler."""
        scheduler = await task_test_client.create_scheduler()
        assert scheduler is not None
        assert task_test_client.scheduler is scheduler

        # Scheduler is created but not started in tests

    @pytest.mark.skip(reason="Async fixture compatibility issues with pytest 9")
    @pytest.mark.asyncio
    async def test_verify_task_completion(self, task_test_client: TaskTestClient):
        """Test verifying task completion."""
        # Enqueue tasks
        task_ids = await task_test_client.enqueue_test_tasks()

        # For mock provider, tasks are immediately available
        # In real scenario, we'd need to process them
        completed = await task_test_client.verify_task_completion(task_ids)
        # Mock provider doesn't actually execute tasks, so this will be False
        # This tests the verification logic
        assert completed is False

    @pytest.mark.skip(reason="Async fixture compatibility issues with pytest 9")
    @pytest.mark.asyncio
    async def test_full_task_workflow(self, task_test_client: TaskTestClient):
        """Test full task workflow."""
        # Start provider
        provider = await task_test_client.start_provider()

        # Create sample task
        task = JobProtocol(
            id="workflow_task",
            name="email_notification",
            args=("workflow@example.com", "Workflow test"),
            kwargs={},
            priority=Priority.NORMAL,
        )

        # Enqueue task
        job = JobProtocol(
            id="workflow_task",
            name="email_notification",
            args=("workflow@example.com", "Workflow test"),
            kwargs={},
            priority=Priority.NORMAL,
        )
        task_id = await provider.enqueue_job(job)
        assert task_id == "workflow_task"

        # Execute the task manually since provider doesn't auto-execute
        result = await task_test_client.execute_test_task(task)
        assert result.success

        # Verify execution in test bed
        executed = task_test_client.test_bed.get_executed_tasks()
        assert len(executed) == 1


class TestTaskIntegration:
    """Test task component integration."""

    @pytest.mark.skip(reason="Async fixture compatibility issues with pytest 9")
    @pytest.mark.asyncio
    async def test_memory_queue_provider_integration(
        self, task_test_client: TaskTestClient,
    ):
        """Test integration with memory queue provider."""
        async with task_test_client.task_context("memory") as provider:
            assert provider is not None

            # Create and enqueue task
            job = JobProtocol(
                id="mem_task",
                name="test_task",
                args=("memory",),
                kwargs={},
                priority=Priority.NORMAL,
            )
            task_id = await provider.enqueue_job(job)
            assert task_id == "mem_task"

            # Check that job was enqueued (can't get individual tasks from provider)
            # This test verifies the provider accepts jobs

    @pytest.mark.skip(reason="Async fixture compatibility issues with pytest 9")
    @pytest.mark.asyncio
    async def test_task_error_handling(self, task_test_client: TaskTestClient):
        """Test task error handling."""
        # Create task that might fail
        task = JobProtocol(
            id="error_task",
            name="failing_task",
            args=(),
            kwargs={},
            priority=Priority.NORMAL,
        )

        # Mock executor to simulate failure
        original_execute = task_test_client.test_bed.mock_executor.execute_task

        async def failing_execute(task):
            if task.name == "failing_task":
                raise TaskExecutionError("Simulated failure")
            return await original_execute(task)

        task_test_client.test_bed.mock_executor.execute_task = failing_execute

        try:
            result = await task_test_client.execute_test_task(task)
            # Should still return a result (failed)
            assert not result.success
        finally:
            # Restore original method
            task_test_client.test_bed.mock_executor.execute_task = original_execute

    @pytest.mark.skip(reason="Async fixture compatibility issues with pytest 9")
    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, task_test_client: TaskTestClient):
        """Test concurrent task execution."""
        tasks = [
            JobProtocol(
                id=f"concurrent_{i}",
                name="email_notification",
                args=(f"user{i}@example.com", f"Message {i}"),
                kwargs={},
                priority=Priority.NORMAL,
            )
            for i in range(5)
        ]

        # Execute tasks concurrently
        results = await asyncio.gather(
            *list(map(lambda task: task_test_client.execute_test_task(task), tasks)),
        )

        # All should succeed
        assert all(result.success for result in results)
        assert len(results) == 5

        # Check execution tracking
        executed = task_test_client.test_bed.get_executed_tasks()
        assert len(executed) == 5
