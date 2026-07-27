import json
from datetime import UTC, datetime
from typing import Any

from lexigram.contracts import DatabaseProviderProtocol
from lexigram.sql.repositories.generic_repository import GenericRepository

from shorts_creator.models.asset import Asset


class _AssetRepo(GenericRepository[Asset, str]):
    def _entity_to_dict(self, entity: Asset) -> dict[str, str | None]:
        d = entity.model_dump()
        d["tags"] = json.dumps(d["tags"])
        d["meta"] = json.dumps(d["meta"])
        return d

    def _row_to_entity(self, row: dict[str, str | None]) -> Asset:
        data = dict(row)
        tags = data.get("tags")
        meta = data.get("meta")
        payload: dict[str, Any] = {
            **data,
            "tags": json.loads(tags) if isinstance(tags, str) else [],
            "meta": json.loads(meta) if isinstance(meta, str) else {},
        }
        return self.entity_class(**payload)

    async def save_many(self, entities: list[Asset]) -> list[Asset]:
        for entity in entities:
            await self.save(entity)
        return entities

    async def delete_many(self, item_ids: list[str]) -> int:
        deleted = 0
        for item_id in item_ids:
            if await self.delete(item_id):
                deleted += 1
        return deleted


class AssetRepository:
    def __init__(self, provider: DatabaseProviderProtocol):
        self._repo = _AssetRepo(
            provider=provider,
            table_name="assets",
            entity_class=Asset,
            key_field="id",
        )
        self._provider = provider

    async def create(self, asset: Asset) -> Asset:
        data = self._repo._entity_to_dict(asset)
        result = await self._provider.execute_insert("assets", data)
        if not result.success:
            raise RuntimeError(result.error_message)
        return asset

    async def update(self, asset_id: str, updates: dict) -> Asset | None:
        asset = await self.get(asset_id)
        if not asset:
            return None
        for key, value in updates.items():
            if hasattr(asset, key):
                setattr(asset, key, value)
        asset.updated_at = datetime.now(UTC)
        await self._provider.execute_update(
            "assets",
            self._repo._entity_to_dict(asset),
            '"id" = ?',
            [asset_id],
        )
        return asset

    async def get(self, asset_id: str) -> Asset | None:
        return await self._repo.find_by_id(asset_id)

    async def list_by_type(self, asset_type: str, role: str | None = None) -> list[Asset]:
        filters: dict = {"type": asset_type}
        if role:
            filters["role"] = role
        return await self._repo.find(
            filters=filters,
            limit=500,
            sort_by="created_at",
            sort_order="desc",
        )

    async def list_all(self) -> list[Asset]:
        return await self._repo.find(limit=1000, sort_by="created_at", sort_order="desc")

    async def delete(self, asset_id: str) -> bool:
        return await self._repo.delete_by_id(asset_id)
