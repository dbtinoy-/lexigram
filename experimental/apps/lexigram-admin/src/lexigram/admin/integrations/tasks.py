"""Tasks integration — dispatches bulk actions through a task queue."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class _NoOpTasks:
    async def dispatch(
        self, runner: str, action_name: str, record_ids: list[str], ctx_summary: str
    ) -> dict[str, Any]:
        return {"status": "noop"}


class TasksIntegration:
    """Adapter that dispatches bulk actions via lexigram-tasks.

    Gracefully no-ops when ``lexigram-tasks`` is not installed or the
    integration is disabled.
    """

    def __init__(self, config: Any) -> None:
        self._config = config
        self._tasks: Any = _NoOpTasks()
        self._enabled = False

    def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.admin.config import TasksIntegrationConfig
        from lexigram.admin.integrations._optional import is_installed

        cfg = self._config
        if not isinstance(cfg, TasksIntegrationConfig):
            cfg = TasksIntegrationConfig()
        if not cfg.enabled:
            self._tasks = _NoOpTasks()
            return
        if not is_installed("lexigram.tasks"):
            self._tasks = _NoOpTasks()
            return
        self._enabled = True

    async def boot(self, container: ContainerResolverProtocol) -> None:
        if not self._enabled:
            return
        try:
            from lexigram.contracts.infra.tasks import TaskQueueProtocol

            self._tasks = await container.resolve(TaskQueueProtocol)
        except Exception:  # noqa: BLE001
            self._tasks = _NoOpTasks()

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy" if not isinstance(self._tasks, _NoOpTasks) else "noop"
        }

    async def dispatch(
        self,
        runner: str,
        action_name: str,
        record_ids: list[str],
        ctx_summary: str,
    ) -> dict[str, Any]:
        """Dispatch through a native dispatcher or enqueue a canonical job.

        ``TaskQueueProtocol`` exposes ``enqueue(JobProtocol)``; it does not
        expose the ad-hoc ``dispatch`` method the first adapter used. Support
        both shapes so custom task integrations keep working while the
        first-party queue receives a valid job object.
        """
        dispatcher = getattr(self._tasks, "dispatch", None)
        if callable(dispatcher):
            result = dispatcher(runner, action_name, record_ids, ctx_summary)
            result = await result if inspect.isawaitable(result) else result
            if isinstance(result, dict):
                return result
            if hasattr(result, "is_ok") and callable(result.is_ok):
                if not result.is_ok():
                    return {"status": "error", "error": str(result.unwrap_err())}
                result = result.unwrap()
            return {"status": "queued", "task_id": str(result)}

        enqueue = getattr(self._tasks, "enqueue", None)
        if not callable(enqueue):
            return {"status": "unavailable"}

        from lexigram.tasks.models.job import JobProtocol

        job = JobProtocol(
            id="",
            name=runner,
            kwargs={
                "action_name": action_name,
                "record_ids": list(record_ids),
                "context": ctx_summary,
            },
        )
        result = await enqueue(job)
        if hasattr(result, "is_ok") and callable(result.is_ok):
            if not result.is_ok():
                error = result.unwrap_err()
                return {"status": "error", "error": str(error)}
            task_id = result.unwrap()
        else:
            task_id = result
        return {"status": "queued", "task_id": str(task_id or job.id)}

    @property
    def threshold(self) -> int:
        return getattr(self._config, "bulk_threshold", 25)


__all__ = ["TasksIntegration"]
