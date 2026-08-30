"""Runtime task registration and wrapper execution tests."""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock

import pytest

from lexigram.tasks import MemoryTaskQueue, task
from lexigram.tasks.decorators import _clear_registered_tasks, unwrap_task_handler
from lexigram.tasks.di.provider import TaskProvider
from lexigram.tasks.execution.registry import HandlerRegistry
from lexigram.tasks.execution.worker import TaskWorker
from lexigram.tasks.models.job import JobProtocol


class _ContainerStub:
    async def resolve_optional(self, contract: type[object]) -> object | None:
        return None

    async def resolve(self, contract: type[object]) -> object | None:
        return None


def _write_task_package(tmp_path: Path, package_name: str, module_name: str) -> str:
    package_root = tmp_path / package_name
    package_root.mkdir(parents=True, exist_ok=True)
    (package_root / "__init__.py").write_text("")
    module_path = package_root / f"{module_name}.py"
    module_path.write_text(
        "from lexigram.tasks import scheduled, task\n\n"
        "@scheduled(cron='*/15 * * * *', name='cleanup')\n"
        "async def cleanup() -> dict[str, bool]:\n"
        "    return {'ok': True}\n\n"
        "@task(name='send_confirmation')\n"
        "async def send_confirmation(order_id: str) -> dict[str, str]:\n"
        "    return {'order_id': order_id}\n"
    )
    return f"{package_name}.{module_name}"


@pytest.mark.asyncio
async def test_task_provider_boot_discovers_already_imported_tasks() -> None:
    """Decorated tasks in imported application modules need no hand wiring."""
    _clear_registered_tasks()

    @task(name="already_imported")
    async def already_imported() -> dict[str, bool]:
        return {"ok": True}

    provider = TaskProvider(
        queue=MemoryTaskQueue(),
        worker_count=1,
        enable_scheduler=False,
    )
    try:
        await provider.boot(_ContainerStub())
        assert provider.registry.get("already_imported") is unwrap_task_handler(
            already_imported
        )
    finally:
        await provider.shutdown()
        _clear_registered_tasks()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task_modules", "task_packages"),
    [(["demo_task_app.jobs"], []), ([], ["demo_task_app"])],
)
async def test_task_provider_boot_autodiscovers_decorated_tasks(
    tmp_path: Path,
    task_modules: list[str],
    task_packages: list[str],
) -> None:
    """Configured task modules and packages should register decorated tasks."""
    package_name = "demo_task_app"
    module_name = "jobs"
    module_path = _write_task_package(tmp_path, package_name, module_name)
    sys.path.insert(0, str(tmp_path))

    provider: TaskProvider | None = None
    try:
        provider = TaskProvider(
            queue=MemoryTaskQueue(),
            worker_count=1,
            enable_scheduler=True,
            task_modules=task_modules,
            task_packages=task_packages,
        )
        await provider.boot(_ContainerStub())

        handlers = provider.registry.to_dict()
        assert "cleanup" in handlers
        assert "send_confirmation" in handlers

        scheduled = provider.get_scheduled_jobs()
        assert scheduled is not None
        assert [(job["name"], job["cron"]) for job in scheduled["scheduled_jobs"]] == [
            ("cleanup", "*/15 * * * *")
        ]
    finally:
        if provider is not None:
            await provider.shutdown()
        _clear_registered_tasks((package_name,))
        sys.modules.pop(module_path, None)
        sys.modules.pop(package_name, None)
        sys.path = [entry for entry in sys.path if entry != str(tmp_path)]


def test_register_handler_unwraps_task_wrappers_and_refreshes_pool() -> None:
    """Late handler registrations should refresh workers and store raw callables."""
    provider = TaskProvider(queue=MemoryTaskQueue(), enable_scheduler=False)
    provider.worker_pool = MagicMock()

    @task(name="send_confirmation")
    async def send_confirmation(order_id: str) -> dict[str, str]:
        return {"order_id": order_id}

    provider.register_handler("send_confirmation", send_confirmation)

    assert provider.registry.get("send_confirmation") is unwrap_task_handler(
        send_confirmation
    )
    provider.worker_pool.refresh_handlers.assert_called_once_with()


@pytest.mark.asyncio
async def test_worker_run_handler_awaits_task_wrapper() -> None:
    """Callable task wrappers should execute their async bodies, not leak coroutines."""
    calls: list[int] = []

    @task(name="double")
    async def double(value: int) -> int:
        calls.append(value)
        return value * 2

    worker = TaskWorker(
        "worker-1",
        queue=MagicMock(),
        handler_registry={"double": double},
    )
    job = JobProtocol(id="job-1", name="double", args=(3,), max_retries=0)

    result = await worker._run_handler(double, job)

    assert result == 6
    assert calls == [3]


@pytest.mark.asyncio
async def test_handler_registry_execute_awaits_task_wrapper() -> None:
    """Registry dispatch should await wrapper objects returned by ``@task``."""
    registry = HandlerRegistry()

    @task(name="triple")
    async def triple(value: int) -> int:
        return value * 3

    registry.register("triple", triple)
    result = await registry.execute(JobProtocol(id="job-2", name="triple", args=(4,)))

    assert result == 12
