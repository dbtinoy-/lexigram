"""Provider lifecycle — wires repositories and services into DI.

The provider is the bridge between the framework's DI container and
your application code.  ``register()`` binds services, ``boot()``
performs post-registration setup, ``shutdown()`` cleans up.

Simplest patterns for new users:
  - register() creates instances and binds them into the container
  - boot() runs after all providers are registered (for cross-cutting setup)
  - shutdown() cleans up resources (close connections, flush buffers)
"""

from __future__ import annotations

from lexigram.di.provider import Provider


class TaskProvider(Provider):
    """Registers repositories, services, and seed data.

    The provider reads the ``task_app:`` section from yaml and
    registers all task management services into the DI container.
    """

    def register(self) -> None:
        """Bind repositories and services.

        The DI container resolves dependencies lazily — a service
        requesting ``UserRepository`` gets the singleton instance
        that was bound here.
        """
        from taskapp.domain import User, UserRole, Project, ProjectStatus, Task, TaskStatus

        # Seed data for the demo
        self._users: dict[int, User] = {
            1: User(id=1, name="Alice", email="alice@example.com", role=UserRole.ADMIN),
            2: User(id=2, name="Bob", email="bob@example.com", role=UserRole.MEMBER),
        }

        self._projects: dict[int, Project] = {
            1: Project(id=1, name="Website Redesign", owner_id=1),
            2: Project(id=2, name="Mobile App", owner_id=2),
        }

        self._tasks: dict[int, Task] = {
            1: Task(id=1, title="Design homepage", project_id=1, assignee_id=1),
            2: Task(id=2, title="Implement auth", project_id=1, assignee_id=2),
            3: Task(id=3, title="Build UI components", project_id=2, assignee_id=1),
        }

    def boot(self) -> None:
        """Post-registration setup — seed data is already in memory."""

    def shutdown(self) -> None:
        """Clean up resources — nothing to do for in-memory demo."""


__all__ = ["TaskProvider"]
