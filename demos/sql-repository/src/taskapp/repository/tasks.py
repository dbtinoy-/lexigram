"""Task repository — maps Task entities to the ``tasks`` table."""

from __future__ import annotations

from typing import Any

from lexigram.sql.repositories.base import SQLRepository
from taskapp.domain import Task, TaskStatus


class TaskRepository(SQLRepository[Task, int]):
    """CRUD operations for Task entities."""

    def __init__(self, provider: Any) -> None:
        super().__init__(
            provider=provider,
            table_name="tasks",
            key_field="id",
        )

    def _entity_to_dict(self, entity: Task) -> dict[str, Any]:
        return {
            "title": entity.title,
            "project_id": entity.project_id,
            "assignee_id": entity.assignee_id,
            "status": entity.status.value,
            "priority": entity.priority,
        }

    def _row_to_entity(self, row: dict[str, Any]) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            project_id=row["project_id"],
            assignee_id=row["assignee_id"],
            status=TaskStatus(row["status"]),
            priority=row["priority"],
        )


__all__ = ["TaskRepository"]
