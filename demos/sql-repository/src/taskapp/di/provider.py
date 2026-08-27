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

Lifecycle:
  1. ``register()`` — declare bindings (no resolution)
  2. ``boot()`` — resolve cross-module deps, create instances, bind
  3. ``shutdown()`` — cleanup (not needed for in-memory stores)

For full reference see:
- ``lexigram.di.provider.Provider`` — base provider class
- ``lexigram.contracts.core.di`` — container protocols
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
    """Bind the task management services as container-managed singletons.

    This provider demonstrates the full lifecycle:
    - ``register()`` declares the config and controller bindings
    - ``boot()`` creates in-memory stores and wires the controller
    - ``health_check()`` reports readiness status
    """

    name = "task_app"

    # Config binding — the framework injects the typed YAML section here
    config_key: str | None = "task_app"
    config_model: type | None = TaskAppConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; concrete wiring happens in :meth:`boot`.

        This method runs AFTER the framework has loaded the config.
        ``self.config`` contains the typed ``TaskAppConfig`` instance
        with YAML values + env overrides already merged.
        """
        cfg = self.config or TaskAppConfig()

        # Bind the config as a singleton — other services can resolve it
        container.singleton(TaskAppConfig, instance=cfg)

        # Class bindings so the keys exist; boot() replaces them with
        # fully-wired instances via container.bind().
        container.singleton(TasksApiController, TasksApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve cross-module dependencies and bind concrete instances.

        This method runs AFTER all providers have registered.
        Resolution is safe — all bindings are in place.
        """
        from taskapp.repository.fixtures import PROJECTS, TASKS, USERS

        cfg = await container.resolve(TaskAppConfig)

        # In production, replace with lexigram-sql repositories:
        #   from lexigram_sql import SQLRepository
        #   users_repo = SQLRepository(UserModel, db_provider)

        # Bind the wired controller — the router resolves this for
        # every request, so per-request resolution reuses the same instance.
        container.bind(
            TasksApiController,
            TasksApiController(
                users_store=dict(USERS),
                projects_store=dict(PROJECTS),
                tasks_store=dict(TASKS),
            ),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the task manager.

        Called by the framework's health check system.  Return
        HEALTHY if the service is ready to handle requests.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
