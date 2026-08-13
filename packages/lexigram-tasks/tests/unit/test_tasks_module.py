"""Tests for tasks module."""

import pytest
from lexigram.tasks import TasksModule
from lexigram.di.module import DynamicModule


class TestTasksModule:
    def test_tasks_module_exists(self) -> None:
        assert TasksModule is not None

    def test_configure_with_defaults(self) -> None:
        result = TasksModule.configure()
        assert isinstance(result, DynamicModule)
        assert result.module is TasksModule

    def test_configure_exports_task_queue(self) -> None:
        from lexigram.contracts.infra.tasks import TaskQueueProtocol

        result = TasksModule.configure()
        assert TaskQueueProtocol in result.exports

    def test_configure_exports_task_executor(self) -> None:
        from lexigram.contracts.infra.tasks import TaskExecutorProtocol

        result = TasksModule.configure()
        assert TaskExecutorProtocol in result.exports

    def test_configure_with_custom_worker_count(self) -> None:
        result = TasksModule.configure(worker_count=4)
        assert isinstance(result, DynamicModule)

    def test_configure_with_scheduler_disabled(self) -> None:
        result = TasksModule.configure(enable_scheduler=False)
        assert isinstance(result, DynamicModule)
