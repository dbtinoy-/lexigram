"""Minimal tests for task components."""
import pytest

from lexigram.testing.clients.tasks import TaskTestBed, TaskTestClient, TaskTestData


@pytest.mark.asyncio
async def test_task_test_data():
    """Test TaskTestData provides sample data."""
    tasks = TaskTestData.sample_tasks()
    assert len(tasks) == 3
    assert tasks[0]["name"] == "email_notification"
    assert tasks[1]["name"] == "data_processing"
    assert tasks[2]["name"] == "cleanup_job"

    jobs = TaskTestData.sample_jobs()
    assert len(jobs) == 2
    assert jobs[0]["name"] == "batch_import"
    assert jobs[1]["name"] == "maintenance"

    scheduled = TaskTestData.sample_scheduled_jobs()
    assert len(scheduled) == 2
    assert scheduled[0]["name"] == "daily_backup"
    assert scheduled[1]["name"] == "hourly_cleanup"


@pytest.mark.asyncio
async def test_mock_task_queue():
    """Test MockTaskQueue basic operations."""
    from lexigram.tasks import JobProtocol, Priority
    from lexigram.testing.clients.tasks import MockTaskQueue

    queue = MockTaskQueue()
    task = JobProtocol(
        id="test_task",
        name="test_task",
        args=("arg1",),
        kwargs={},
        priority=Priority.NORMAL,
    )

    # Test enqueue
    enqueue_result = await queue.enqueue(task)
    assert enqueue_result.is_ok()
    task_id = enqueue_result.unwrap()
    assert task_id == "test_task"

    # Test dequeue
    dequeued = await queue.dequeue()
    assert dequeued is not None
    assert dequeued.id == "test_task"

    # Test stats
    stats = await queue.get_queue_stats()
    assert "queued" in stats
    assert "completed" in stats


@pytest.mark.asyncio
async def test_mock_task_executor():
    """Test MockTaskExecutor basic operations."""
    from lexigram.tasks import JobProtocol, Priority
    from lexigram.testing.clients.tasks import MockTaskExecutor

    executor = MockTaskExecutor()
    task = JobProtocol(
        id="test_task",
        name="email_notification",
        args=("user@example.com", "Test message"),
        kwargs={},
        priority=Priority.NORMAL,
    )

    # Test execution
    result = await executor.execute_task(task)
    assert result.success
    assert result.value["task_id"] == "test_task"
    assert "sent" in result.value

    # Test stats
    stats = await executor.get_execution_stats()
    assert stats["executed"] == 1
    assert stats["successful"] == 1


@pytest.mark.asyncio
async def test_task_test_bed_setup():
    """Test TaskTestBed setup and teardown."""
    test_bed = TaskTestBed()
    await test_bed.setup()

    assert test_bed.mock_queue is not None
    assert test_bed.mock_executor is not None

    # Test bed should be set up with sample data
    enqueued = test_bed.get_enqueued_tasks()
    assert len(enqueued) == 3

    await test_bed.teardown()


@pytest.mark.asyncio
async def test_task_test_client_provider_lifecycle():
    """Test TaskTestClient provider lifecycle."""
    test_bed = TaskTestBed()
    await test_bed.setup()

    client = TaskTestClient(test_bed)

    # Start provider
    provider = await client.start_provider()
    assert provider is not None
    assert client.provider is provider

    # Stop provider
    await client.stop_provider()
    assert client.provider is None

    await test_bed.teardown()


@pytest.mark.asyncio
async def test_task_test_client_enqueue_tasks():
    """Test TaskTestClient enqueuing test tasks."""
    test_bed = TaskTestBed()
    await test_bed.setup()

    client = TaskTestClient(test_bed)

    # Enqueue tasks
    task_ids = await client.enqueue_test_tasks()
    assert len(task_ids) == 3

    # Verify tasks were enqueued
    enqueued = test_bed.get_enqueued_tasks()
    assert len(enqueued) == 6  # 3 from setup + 3 enqueued

    await test_bed.teardown()


@pytest.mark.asyncio
async def test_task_test_client_execute_task():
    """Test TaskTestClient executing a test task."""
    test_bed = TaskTestBed()
    await test_bed.setup()

    client = TaskTestClient(test_bed)

    from lexigram.tasks import JobProtocol, Priority

    task = JobProtocol(
        id="test_exec",
        name="data_processing",
        args=([1, 2, 3],),
        kwargs={},
        priority=Priority.NORMAL,
    )

    result = await client.execute_test_task(task)
    assert result.success
    assert result.value["task_id"] == "test_exec"
    assert result.value["result"] == 6  # sum of [1, 2, 3]

    await test_bed.teardown()


@pytest.mark.asyncio
async def test_task_test_client_context_manager():
    """Test TaskTestClient context manager."""
    test_bed = TaskTestBed()
    await test_bed.setup()

    client = TaskTestClient(test_bed)

    async with client.task_context() as provider:
        assert provider is not None
        assert client.provider is provider

    # Provider should be stopped after context
    assert client.provider is None

    await test_bed.teardown()
