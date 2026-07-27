from typing import Any

from lexigram.contracts import DatabaseProviderProtocol
from lexigram.sql.repositories.generic_repository import GenericRepository

from shorts_creator.models.project import Project


class _ProjectRepo(GenericRepository[Project, str]):
    def _entity_to_dict(self, entity: Project) -> dict[str, Any]:
        return entity.model_dump()

    def _row_to_entity(self, row: dict[str, Any]) -> Project:
        return self.entity_class(**dict(row))

    async def save_many(self, entities: list[Project]) -> list[Project]:
        for entity in entities:
            await self.save(entity)
        return entities

    async def delete_many(self, item_ids: list[str]) -> int:
        deleted = 0
        for item_id in item_ids:
            if await self.delete(item_id):
                deleted += 1
        return deleted


class ProjectRepository:
    def __init__(self, provider: DatabaseProviderProtocol):
        self._repo = _ProjectRepo(
            provider=provider,
            table_name="projects",
            entity_class=Project,
            key_field="id",
        )
        self._provider = provider

    async def create(self, project: Project) -> Project:
        data = project.model_dump()
        result = await self._provider.execute_insert("projects", data)
        if not result.success:
            raise RuntimeError(result.error_message)
        return project

    async def update(self, project: Project) -> Project:
        data = project.model_dump()
        from datetime import UTC, datetime

        data["updated_at"] = datetime.now(UTC)
        result = await self._provider.execute_update(
            "projects",
            data,
            '"id" = ?',
            [project.id],
        )
        if not result.success:
            raise RuntimeError(result.error_message or f"update failed for project {project.id}")
        return project

    async def get(self, project_id: str) -> Project | None:
        return await self._repo.find_by_id(project_id)

    async def list_recent(self, limit: int = 50) -> list[Project]:
        return await self._repo.find(limit=limit, sort_by="created_at", sort_order="desc")

    async def delete(self, project_id: str) -> bool:
        return await self._repo.delete_by_id(project_id)
