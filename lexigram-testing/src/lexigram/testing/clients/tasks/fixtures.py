"""
Pytest fixtures for task testing.

Provides comprehensive fixtures for testing task processing, queuing,
execution, scheduling, and worker management.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import Any, cast

import pytest

from lexigram.testing.clients.tasks.client import (  # type: ignore[attr-defined]
    MockTaskExecutor,
    MockTaskQueue,
    TaskTestBed,
    TaskTestClient,
    TaskTestData,
)

pytest_asyncio: Any = None
try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

# Make decorator variable explicitly typed to avoid mypy 'untyped decorator' warnings
_fixture: Callable[..., Any] = (
    pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
)


@_fixture
async def task_test_bed() -> AsyncGenerator[TaskTestBed, None]:
    """Create a task test bed."""
    test_bed = TaskTestBed()
    await test_bed.setup()
    try:
        yield test_bed
    finally:
        await test_bed.teardown()


@_fixture
async def task_test_client(
    task_test_bed: TaskTestBed,
) -> AsyncGenerator[TaskTestClient, None]:
    """Create a task test client."""
    client = task_test_bed.create_test_client()  # type: ignore[attr-defined]
    yield client
    await client.stop_provider()


@_fixture
async def task_provider(task_test_client: TaskTestClient) -> AsyncGenerator[Any, None]:
    """Create a task provider."""
    async with task_test_client.task_context() as provider:
        yield provider


@_fixture
async def task_worker_pool(
    task_test_client: TaskTestClient,
) -> AsyncGenerator[Any, None]:
    """Create a task worker pool."""
    worker_pool = await task_test_client.create_worker_pool()  # type: ignore[attr-defined]
    yield worker_pool
    await worker_pool.stop()


@pytest.fixture
def mock_task_queue() -> MockTaskQueue:
    """Create a mock task queue."""
    return MockTaskQueue()


@pytest.fixture
def mock_task_executor() -> MockTaskExecutor:
    """Create a mock task executor."""
    return MockTaskExecutor()


@pytest.fixture
def sample_tasks() -> list[dict[str, Any]]:
    """Create sample tasks for testing."""
    return TaskTestData.sample_tasks()


@pytest.fixture
def sample_jobs() -> list[dict[str, Any]]:
    """Create sample jobs for testing."""
    return TaskTestData.sample_jobs()


@pytest.fixture
def sample_scheduled_jobs() -> list[dict[str, Any]]:
    """Create sample scheduled jobs for testing."""
    return TaskTestData.sample_scheduled_jobs()


@pytest.fixture
def sample_worker_configs() -> list[dict[str, Any]]:
    """Create sample worker configurations for testing."""
    return cast(
        "list[dict[str, Any]]",
        TaskTestData.sample_worker_configs(),  # type: ignore[attr-defined]
    )


@pytest.fixture
def task_assertions(task_test_client: TaskTestClient) -> dict[str, Any]:
    """Create assertion helpers for task testing."""
    return {
        "assert_enqueued_count": task_test_client.assert_enqueued_tasks_count,  # type: ignore[attr-defined]
        "assert_executed_count": task_test_client.assert_executed_tasks_count,  # type: ignore[attr-defined]
        "assert_task_success": task_test_client.assert_task_result_success,  # type: ignore[attr-defined]
    }
