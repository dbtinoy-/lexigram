"""Tasks integration — dispatches bulk actions through a task queue."""

from __future__ import annotations

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
        self._tasks: Any = None
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
        return await self._tasks.dispatch(runner, action_name, record_ids, ctx_summary)

    @property
    def threshold(self) -> int:
        return getattr(self._config, "bulk_threshold", 25)


__all__ = ["TasksIntegration"]
