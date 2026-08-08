import json
from typing import Any

from lexigram.contracts import DatabaseProviderProtocol
from lexigram.sql.repositories.generic_repository import GenericRepository

from shorts_creator.models.run import Run


class _RunRepo(GenericRepository[Run, str]):
    def _entity_to_dict(self, entity: Run) -> dict[str, str | None]:
        d = entity.model_dump()
        d["stage_progress"] = json.dumps(d["stage_progress"])
        return d

    def _row_to_entity(self, row: dict[str, str | None]) -> Run:
        data = dict(row)
        stage = data.get("stage_progress")
        payload: dict[str, Any] = {
            **data,
            "stage_progress": json.loads(stage) if isinstance(stage, str) else {},
        }
        return self.entity_class(**payload)

    async def save_many(self, entities: list[Run]) -> list[Run]:
        for entity in entities:
            await self.save(entity)
        return entities

    async def delete_many(self, item_ids: list[str]) -> int:
        deleted = 0
        for item_id in item_ids:
            if await self.delete(item_id):
                deleted += 1
        return deleted


class RunRepository:
    def __init__(self, provider: DatabaseProviderProtocol):
        self._repo = _RunRepo(
            provider=provider,
            table_name="runs",
            entity_class=Run,
            key_field="id",
        )
        self._provider = provider

    async def create(self, run: Run) -> Run:
        data = run.model_dump()
        data["stage_progress"] = json.dumps(data["stage_progress"])
        result = await self._provider.execute_insert("runs", data)
        if not result.success:
            raise RuntimeError(result.error_message)
        return run

    async def update(self, run: Run) -> Run:
        data = run.model_dump()
        data["stage_progress"] = json.dumps(data["stage_progress"])
        from datetime import UTC, datetime

        data["updated_at"] = datetime.now(UTC)
        result = await self._provider.execute_update(
            "runs",
            data,
            '"id" = ?',
            [run.id],
        )
        if not result.success:
            raise RuntimeError(result.error_message or f"update failed for run {run.id}")
        return run

    async def get(self, run_id: str) -> Run | None:
        return await self._repo.find_by_id(run_id)

    async def list_by_project(self, project_id: str, limit: int = 50) -> list[Run]:
        return await self._repo.find(
            filters={"project_id": project_id},
            limit=limit,
            sort_by="created_at",
            sort_order="desc",
        )

    async def list_status(self, status: str, limit: int = 10_000) -> list[Run]:
        return await self._repo.find(
            filters={"status": status},
            limit=limit,
            sort_by="created_at",
            sort_order="asc",
        )

    async def list_recent(self, limit: int = 50) -> list[Run]:
        return await self._repo.find(limit=limit, sort_by="created_at", sort_order="desc")

    async def delete(self, run_id: str) -> bool:
        return await self._repo.delete_by_id(run_id)
