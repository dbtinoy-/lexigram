"""Task service — business logic for task management."""

from __future__ import annotations

from typing import Any

from lexigram.result import Result
from taskapp.domain import Task, TaskStatus


class TaskService:
    """Business operations for tasks."""

    def __init__(self, task_repo: Any) -> None:
        self._repo = task_repo

    async def create_task(
        self,
        title: str,
        project_id: int,
        assignee_id: int | None = None,
        priority: int = 0,
    ) -> Result[Task, str]:
        """Create a new task."""
        if not title:
            return Result.err("Task title is required")
        if project_id <= 0:
            return Result.err("Valid project ID is required")

        task = Task(
            title=title,
            project_id=project_id,
            assignee_id=assignee_id,
            priority=priority,
        )
        created = await self._repo.add(task)
        return Result.ok(created)

    async def get_task(self, task_id: int) -> Result[Task, str]:
        """Get a task by ID."""
        task = await self._repo.get(task_id)
        if task is None:
            return Result.err(f"Task {task_id} not found")
        return Result.ok(task)

    async def list_tasks(self) -> list[Task]:
        """List all tasks."""
        return await self._repo.list()

    async def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
    ) -> Result[Task, str]:
        """Update a task's status."""
        task = await self._repo.get(task_id)
        if task is None:
            return Result.err(f"Task {task_id} not found")

        updated_task = Task(
            id=task.id,
            title=task.title,
            project_id=task.project_id,
            assignee_id=task.assignee_id,
            status=status,
            priority=task.priority,
        )
        updated = await self._repo.update(task_id, updated_task)
        return Result.ok(updated)

    async def delete_task(self, task_id: int) -> Result[bool, str]:
        """Delete a task by ID."""
        deleted = await self._repo.delete(task_id)
        if not deleted:
            return Result.err(f"Task {task_id} not found")
        return Result.ok(True)


__all__ = ["TaskService"]
