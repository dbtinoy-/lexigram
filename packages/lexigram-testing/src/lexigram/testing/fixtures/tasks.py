"""Pytest fixtures for Lexigram Tasks testing."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest

from lexigram.testing.clients.tasks import TaskTestBed, TaskTestClient, TaskTestData


@pytest.fixture
async def task_test_bed() -> AsyncGenerator[TaskTestBed, None]:
    """Fixture for TaskTestBed."""
    return TaskTestBed()  # type: ignore[return-value]


@pytest.fixture
async def task_test_client(task_test_bed: TaskTestBed) -> TaskTestClient:
    """Fixture for TaskTestClient."""
    return TaskTestClient(task_test_bed)


@pytest.fixture
def sample_task_data() -> list[dict[str, Any]]:
    """Fixture for sample task data."""
    return TaskTestData.sample_tasks()


__all__ = ["sample_task_data", "task_test_bed", "task_test_client"]
