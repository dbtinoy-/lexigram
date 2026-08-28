"""HTTP surface for the single-purpose SQL task repository demo."""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, delete, get, post, put
from taskapp.repository.tasks import TaskRepository


class TasksApiController(Controller):
    """Expose repository CRUD without putting SQL in the controller."""

    prefix = "/api/tasks"
    _valid_statuses = {"todo", "in_progress", "done"}

    def __init__(self, repository: TaskRepository | None = None) -> None:
        self._repository = repository

    @post("/tasks")
    async def create_task(self, body: dict[str, Any]) -> dict[str, Any]:
        """Insert a task through ``TaskRepository.create``."""
        title = str(body.get("title", "")).strip()
        if not title:
            return {"error": "Task title is required"}
        try:
            priority = int(body.get("priority", 0))
        except (TypeError, ValueError):
            return {"error": "Priority must be an integer"}
        return {"task": await self._repository.create(title, priority)}

    @get("/tasks")
    async def list_tasks(self) -> list[dict[str, Any]]:
        """List rows read from SQLite through the repository."""
        return await self._repository.list()

    @get("/tasks/{task_id}")
    async def get_task(self, task_id: int) -> dict[str, Any]:
        """Read one task by primary key."""
        task = await self._repository.get(task_id)
        return {"task": task} if task else {"error": f"Task {task_id} not found"}

    @put("/tasks/{task_id}/status")
    async def update_task_status(
        self,
        task_id: int,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a status through a parameterized repository query."""
        status = body.get("status", "todo")
        if status not in self._valid_statuses:
            return {
                "error": f"Invalid status: {status}. Must be one of: {sorted(self._valid_statuses)}"
            }
        task = await self._repository.update_status(task_id, status)
        return {"task": task} if task else {"error": f"Task {task_id} not found"}

    @delete("/tasks/{task_id}")
    async def delete_task(self, task_id: int) -> dict[str, Any]:
        """Delete a task through the database provider."""
        if not await self._repository.delete(task_id):
            return {"error": f"Task {task_id} not found"}
        return {"deleted": True}

    @get("/stats")
    async def stats(self) -> dict[str, Any]:
        """Return aggregate data from SQL, not an in-memory fixture."""
        return await self._repository.stats()


__all__ = ["TasksApiController"]
