"""Provider wiring for the task management demo.

Convention followed: **Provider pattern** — ``TaskProvider`` is the
canonical shape (mirrors ``lexigram-auth`` + the boot-phase ``bind()``
contract in ``lexigram.contracts.core.di``):

- ``register()`` only *declares* bindings.  Zero-arg factories cover
  purely config-derived services; dependency-full services are declared
  as class bindings and instantiated in :meth:`boot`.
- ``boot()`` resolves cross-module dependencies after every provider
  has registered and rebinds the concrete instances via
  ``container.bind()``.
- Controllers are constructed by the router from the container; ``boot``
  binds their prebuilt instances so per-request resolution reuses them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.di.provider import Provider
from taskapp.config import TaskAppConfig
from taskapp.controllers.api import TasksApiController

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

__all__ = ["TaskProvider"]


class TaskProvider(Provider):
    """Bind the task management services as container-managed singletons."""

    name = "task_app"

    config_key: str | None = "task_app"
    config_model: type | None = TaskAppConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; concrete wiring happens in :meth:`boot`."""
        cfg = self.config or TaskAppConfig()

        container.singleton(TaskAppConfig, instance=cfg)

        # Class bindings so the keys exist; boot() replaces them with
        # fully-wired instances via container.bind().
        container.singleton(TasksApiController, TasksApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve cross-module dependencies and bind concrete instances."""
        cfg = await container.resolve(TaskAppConfig)

        # In-memory stores for the demo
        users_store: dict[int, dict] = {
            1: {
                "id": 1,
                "name": "Alice",
                "email": "alice@example.com",
                "role": "admin",
            },
            2: {"id": 2, "name": "Bob", "email": "bob@example.com", "role": "member"},
        }
        projects_store: dict[int, dict] = {
            1: {"id": 1, "name": "Website Redesign", "owner_id": 1, "status": "active"},
            2: {"id": 2, "name": "Mobile App", "owner_id": 2, "status": "active"},
        }
        tasks_store: dict[int, dict] = {
            1: {
                "id": 1,
                "title": "Design homepage",
                "project_id": 1,
                "assignee_id": 1,
                "status": "todo",
                "priority": 0,
            },
            2: {
                "id": 2,
                "title": "Implement auth",
                "project_id": 1,
                "assignee_id": 2,
                "status": "in_progress",
                "priority": 1,
            },
            3: {
                "id": 3,
                "title": "Build UI components",
                "project_id": 2,
                "assignee_id": 1,
                "status": "todo",
                "priority": 0,
            },
        }

        # Bind the wired controller
        container.bind(
            TasksApiController,
            TasksApiController(
                users_store=users_store,
                projects_store=projects_store,
                tasks_store=tasks_store,
            ),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the task manager."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
