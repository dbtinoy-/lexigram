"""Project repository — maps Project entities to the ``projects`` table."""

from __future__ import annotations

from typing import Any

from lexigram.sql.repositories.base import SQLRepository
from taskapp.domain import Project, ProjectStatus


class ProjectRepository(SQLRepository[Project, int]):
    """CRUD operations for Project entities."""

    def __init__(self, provider: Any) -> None:
        super().__init__(
            provider=provider,
            table_name="projects",
            key_field="id",
        )

    def _entity_to_dict(self, entity: Project) -> dict[str, Any]:
        return {
            "name": entity.name,
            "owner_id": entity.owner_id,
            "status": entity.status.value,
        }

    def _row_to_entity(self, row: dict[str, Any]) -> Project:
        return Project(
            id=row["id"],
            name=row["name"],
            owner_id=row["owner_id"],
            status=ProjectStatus(row["status"]),
        )


__all__ = ["ProjectRepository"]
