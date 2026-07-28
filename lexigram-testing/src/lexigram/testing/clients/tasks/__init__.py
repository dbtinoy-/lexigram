"""Testing clients and test beds for lexigram-tasks."""

from __future__ import annotations

from lexigram.testing.clients.tasks.bed import TaskTestBed
from lexigram.testing.clients.tasks.client import TaskTestClient
from lexigram.testing.clients.tasks.data import TaskTestData
from lexigram.testing.clients.tasks.mocks import (
    MockTaskExecutor,
    MockTaskQueue,
    MockTaskResult,
    MockTasksProvider,
)

__all__ = [
    "MockTaskExecutor",
    "MockTaskQueue",
    "MockTaskResult",
    "MockTasksProvider",
    "TaskTestBed",
    "TaskTestClient",
    "TaskTestData",
]
