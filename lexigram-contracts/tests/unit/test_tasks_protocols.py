"""Tests for tasks protocol definitions."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.contracts.infra.tasks.protocols import (
    DLQProtocol,
    JobProtocol,
    JobTemplateProtocol,
    TaskExecutorProtocol,
    TaskProviderProtocol,
    TaskQueueProtocol,
    TaskWorkerProtocol,
)


class TestJobProtocol:
    """Tests for JobProtocol."""

    def test_has_required_attributes(self) -> None:
        """Test protocol has required attributes."""

        class Job:
            id: str = "job-1"
            name: str = "test-job"
            args: tuple = ()
            kwargs: dict = {}
            priority: int = 0
            status: Any = None
            max_retries: int = 3
            timeout: float | None = None
            correlation_id: str | None = None
            causation_id: str | None = None

        job = Job()
        assert job.id == "job-1"
        assert job.name == "test-job"

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Job:
            id: str = ""
            name: str = ""
            args: tuple = ()
            kwargs: dict = {}
            priority: int = 0
            status: Any = None
            max_retries: int = 0
            timeout: float | None = None
            correlation_id: str | None = None
            causation_id: str | None = None

        assert isinstance(Job(), JobProtocol)


class TestTaskQueueProtocol:
    """Tests for TaskQueueProtocol."""

    @pytest.mark.asyncio
    async def test_has_enqueue_method(self) -> None:
        """Test protocol has enqueue async method."""

        from lexigram.result import Ok

        class Queue:
            async def enqueue(self, task: Any) -> Any:
                return Ok("task-id")

        queue = Queue()
        result = await queue.enqueue({})
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_has_dequeue_method(self) -> None:
        """Test protocol has dequeue async method."""

        class Queue:
            async def dequeue(self) -> Any | None:
                return {"id": "task-1"}

        queue = Queue()
        result = await queue.dequeue()
        assert result is not None

    @pytest.mark.asyncio
    async def test_has_get_task_count_method(self) -> None:
        """Test protocol has get_task_count async method."""

        class Queue:
            async def get_task_count(self) -> int:
                return 10

        queue = Queue()
        result = await queue.get_task_count()
        assert result == 10

    @pytest.mark.asyncio
    async def test_has_clear_method(self) -> None:
        """Test protocol has clear async method."""

        class Queue:
            async def clear(self) -> None:
                pass

        queue = Queue()
        await queue.clear()

    @pytest.mark.asyncio
    async def test_has_ack_method(self) -> None:
        """Test protocol has ack async method."""

        class Queue:
            async def ack(self, task_id: str) -> None:
                pass

        queue = Queue()
        await queue.ack("task-1")

    @pytest.mark.asyncio
    async def test_has_nack_method(self) -> None:
        """Test protocol has nack async method."""

        class Queue:
            async def nack(self, task_id: str, requeue: bool = True) -> None:
                pass

        queue = Queue()
        await queue.nack("task-1")

    @pytest.mark.asyncio
    async def test_has_close_method(self) -> None:
        """Test protocol has close async method."""

        class Queue:
            async def close(self) -> None:
                pass

        queue = Queue()
        await queue.close()

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        from lexigram.result import Ok

        class Queue:
            async def enqueue(self, task: Any) -> Any:
                return Ok("")

            async def dequeue(self) -> Any | None:
                return None

            async def get_task_count(self) -> int:
                return 0

            async def clear(self) -> None:
                pass

            async def get_job(self, job_id: str) -> Any | None:
                return None

            async def delete_job(self, job_id: str) -> bool:
                return True

            async def count(self, queue_name: str, status: Any | None = None) -> int:
                return 0

            async def ack(self, task_id: str) -> None:
                pass

            async def nack(self, task_id: str, requeue: bool = True) -> None:
                pass

            async def close(self) -> None:
                pass

        assert isinstance(Queue(), TaskQueueProtocol)


class TestTaskExecutorProtocol:
    """Tests for TaskExecutorProtocol."""

    @pytest.mark.asyncio
    async def test_has_execute_method(self) -> None:
        """Test protocol has execute async method."""

        class Executor:
            async def execute(self, task: Any) -> Any:
                return {"result": "test"}

        executor = Executor()
        result = await executor.execute({})
        assert result["result"] == "test"

    def test_has_register_handler_method(self) -> None:
        """Test protocol has register_handler method."""

        class Executor:
            def register_handler(self, task_name: str, handler: Any) -> None:
                pass

        executor = Executor()
        executor.register_handler("task", lambda: None)

    def test_has_get_handler_method(self) -> None:
        """Test protocol has get_handler method."""

        class Executor:
            def get_handler(self, task_name: str) -> Any | None:
                return None

        executor = Executor()
        result = executor.get_handler("task")
        assert result is None

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Executor:
            async def execute(self, task: Any) -> Any:
                return {}

            def register_handler(self, task_name: str, handler: Any) -> None:
                pass

            def get_handler(self, task_name: str) -> Any | None:
                return None

        assert isinstance(Executor(), TaskExecutorProtocol)


class TestTaskProviderProtocol:
    """Tests for TaskProviderProtocol."""

    @pytest.mark.asyncio
    async def test_has_register_method(self) -> None:
        """Test protocol has register async method."""

        class Provider:
            async def register(self, container: Any) -> None:
                pass

        provider = Provider()
        await provider.register({})

    @pytest.mark.asyncio
    async def test_has_boot_method(self) -> None:
        """Test protocol has boot async method."""

        class Provider:
            async def boot(self, container: Any | None = None) -> None:
                pass

        provider = Provider()
        await provider.boot()

    @pytest.mark.asyncio
    async def test_has_shutdown_method(self) -> None:
        """Test protocol has shutdown async method."""

        class Provider:
            async def shutdown(self, app: Any) -> None:
                pass

        provider = Provider()
        await provider.shutdown({})

    @pytest.mark.asyncio
    async def test_has_health_check_method(self) -> None:
        """Test protocol has health_check async method."""

        class Provider:
            async def health_check(self, timeout: float = 5.0) -> Any:
                return {"status": "healthy"}

        provider = Provider()
        result = await provider.health_check()
        assert result["status"] == "healthy"

    def test_has_register_handler_method(self) -> None:
        """Test protocol has register_handler method."""

        class Provider:
            def register_handler(self, task_name: str, handler: Any) -> None:
                pass

        provider = Provider()
        provider.register_handler("task", lambda: None)

    def test_has_get_worker_stats_method(self) -> None:
        """Test protocol has get_worker_stats method."""

        class Provider:
            def get_worker_stats(self) -> dict[str, Any] | None:
                return {"workers": 5}

        provider = Provider()
        result = provider.get_worker_stats()
        assert result["workers"] == 5

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Provider:
            async def register(self, container: Any) -> None:
                pass

            async def boot(self, container: Any | None = None) -> None:
                pass

            async def shutdown(self, app: Any) -> None:
                pass

            async def health_check(self, timeout: float = 5.0) -> Any:
                return {}

            def register_handler(self, task_name: str, handler: Any) -> None:
                pass

            def register_scheduled_task(self, task_func: Any) -> None:
                pass

            async def enqueue_job(self, job: Any) -> str:
                return ""

            def schedule_job(self, job_template: Any, cron_expression: str, job_id: str | None = None) -> str | None:
                return None

            def unschedule_job(self, job_id: str) -> bool:
                return False

            def get_worker_stats(self) -> dict | None:
                return None

            def get_scheduled_jobs(self) -> dict | None:
                return None

        assert isinstance(Provider(), TaskProviderProtocol)


class TestJobTemplateProtocol:
    """Tests for JobTemplateProtocol."""

    def test_has_required_attributes(self) -> None:
        """Test protocol has required attributes."""

        class Template:
            name: str = "test-job"
            args: tuple = ()
            kwargs: dict = {}
            priority: int = 0
            max_retries: int = 3
            timeout: float | None = None
            depends_on: list = []

        template = Template()
        assert template.name == "test-job"

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Template:
            name: str = ""
            args: tuple = ()
            kwargs: dict = {}
            priority: int = 0
            max_retries: int = 0
            timeout: float | None = None
            depends_on: list = []

        assert isinstance(Template(), JobTemplateProtocol)


class TestTaskWorkerProtocol:
    """Tests for TaskWorkerProtocol."""

    @pytest.mark.asyncio
    async def test_has_start_method(self) -> None:
        """Test protocol has start async method."""

        class Worker:
            def __init__(
                self,
                worker_id: str,
                queue: Any,
                handler_registry: dict[str, Any],
            ) -> None:
                pass

            async def start(self) -> None:
                pass

        worker = Worker("worker-1", {}, {})
        await worker.start()

    @pytest.mark.asyncio
    async def test_has_stop_method(self) -> None:
        """Test protocol has stop async method."""

        class Worker:
            def __init__(
                self,
                worker_id: str,
                queue: Any,
                handler_registry: dict[str, Any],
            ) -> None:
                pass

            async def stop(self) -> None:
                pass

        worker = Worker("worker-1", {}, {})
        await worker.stop()

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Worker:
            def __init__(
                self,
                worker_id: str,
                queue: Any,
                handler_registry: dict[str, Any],
            ) -> None:
                pass

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        assert isinstance(Worker("worker-1", {}, {}), TaskWorkerProtocol)


class TestDLQProtocol:
    """Tests for DLQProtocol."""

    @pytest.mark.asyncio
    async def test_has_add_method(self) -> None:
        """Test protocol has add async method."""

        class DLQ:
            async def add(
                self,
                message_id: str,
                payload: Any,
                reason: str,
                metadata: dict[str, Any] | None = None,
            ) -> None:
                pass

        dlq = DLQ()
        await dlq.add("msg-1", {}, "error")

    @pytest.mark.asyncio
    async def test_has_get_method(self) -> None:
        """Test protocol has get async method."""

        class DLQ:
            async def get(self, message_id: str) -> dict[str, Any] | None:
                return {"id": message_id}

        dlq = DLQ()
        result = await dlq.get("msg-1")
        assert result["id"] == "msg-1"

    @pytest.mark.asyncio
    async def test_has_retry_method(self) -> None:
        """Test protocol has retry async method."""

        class DLQ:
            async def retry(self, message_id: str) -> bool:
                return True

        dlq = DLQ()
        result = await dlq.retry("msg-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_has_purge_method(self) -> None:
        """Test protocol has purge async method."""

        class DLQ:
            async def purge(self, message_id: str) -> bool:
                return True

        dlq = DLQ()
        result = await dlq.purge("msg-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_has_clear_method(self) -> None:
        """Test protocol has clear async method."""

        class DLQ:
            async def clear(self) -> int:
                return 5

        dlq = DLQ()
        result = await dlq.clear()
        assert result == 5

    @pytest.mark.asyncio
    async def test_has_size_method(self) -> None:
        """Test protocol has size async method."""

        class DLQ:
            async def size(self) -> int:
                return 10

        dlq = DLQ()
        result = await dlq.size()
        assert result == 10

    @pytest.mark.asyncio
    async def test_has_list_failed_method(self) -> None:
        """Test protocol has list_failed async method."""

        class DLQ:
            async def list_failed(
                self,
                limit: int = 100,
                offset: int = 0,
            ) -> list[dict[str, Any]]:
                return []

        dlq = DLQ()
        result = await dlq.list_failed()
        assert isinstance(result, list)

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class DLQ:
            async def add(self, message_id: str, payload: Any, reason: str, metadata: dict | None = None) -> None:
                pass

            async def get(self, message_id: str) -> dict | None:
                return None

            async def retry(self, message_id: str) -> bool:
                return False

            async def purge(self, message_id: str) -> bool:
                return False

            async def clear(self) -> int:
                return 0

            async def size(self) -> int:
                return 0

            async def list_failed(self, limit: int = 100, offset: int = 0) -> list:
                return []

        assert isinstance(DLQ(), DLQProtocol)
