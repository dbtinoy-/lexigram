"""Tests for belongs-to-many pivot persistence backed by a data source."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.relations.belongs_to_many import BelongsToManyRelationManager
from lexigram.admin.relations.errors import RelationPersistenceError


class _PivotDataSource:
    """In-memory pivot data source recording operations."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self._next_id = 1
        self.created: list[dict[str, Any]] = []
        self.deleted_ids: list[Any] = []
        self.updated: list[tuple[Any, dict[str, Any]]] = []

    async def find_many(self, query: Any) -> Any:
        return SimpleNamespace(items=list(self.rows))

    async def create(self, data: dict[str, Any]) -> Any:
        self.created.append(dict(data))
        row = {**data, "id": self._next_id}
        self._next_id += 1
        self.rows.append(row)
        return row

    async def bulk_delete(self, ids: list[Any]) -> int:
        self.deleted_ids.extend(ids)
        self.rows = [r for r in self.rows if r["id"] not in ids]
        return len(ids)

    async def update(self, item_id: Any, data: dict[str, Any]) -> Any:
        self.updated.append((item_id, data))
        for row in self.rows:
            if row["id"] == item_id:
                row.update(data)
                return row
        return None


class SimpleNamespace:
    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)


class _RolesManager(BelongsToManyRelationManager):
    async def get_query(self) -> list[Any]:
        return []


def _manager(data_source: _PivotDataSource | None = None) -> BelongsToManyRelationManager:
    manager = _RolesManager(parent_id="parent-1")
    manager.pivot_table = "user_roles"
    manager.pivot_columns = ["is_primary"]
    manager.related_key = "role_id"
    manager.related_key_local = "user_id"
    if data_source is not None:
        manager.set_data_source(data_source)
    return manager


@pytest.mark.asyncio
async def test_attach_persists_pivot_row() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)

    await manager.attach("role-1", {"is_primary": True})

    assert ds.created == [
        {"user_id": "parent-1", "role_id": "role-1", "is_primary": True},
    ]


@pytest.mark.asyncio
async def test_attach_filters_pivot_data_to_configured_columns() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)

    await manager.attach("role-1", {"is_primary": True, "junk": "nope"})

    assert "junk" not in ds.created[0]


@pytest.mark.asyncio
async def test_get_attached_ids() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)
    await manager.attach("role-1")
    await manager.attach("role-2")

    assert await manager.get_attached_ids() == ["role-1", "role-2"]


@pytest.mark.asyncio
async def test_get_attached_ids_without_data_source_returns_empty() -> None:
    manager = _manager()
    assert await manager.get_attached_ids() == []


@pytest.mark.asyncio
async def test_detach_removes_matching_pivot_rows() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)
    await manager.attach("role-1")
    await manager.attach("role-2")

    await manager.detach("role-1")

    assert await manager.get_attached_ids() == ["role-2"]
    assert len(ds.deleted_ids) == 1


@pytest.mark.asyncio
async def test_get_pivot_data() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)
    await manager.attach("role-1", {"is_primary": True})

    assert await manager.get_pivot_data("role-1") == {"is_primary": True}
    assert await manager.get_pivot_data("role-9") is None


@pytest.mark.asyncio
async def test_update_pivot() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)
    await manager.attach("role-1", {"is_primary": False})

    await manager.update_pivot("role-1", {"is_primary": True})

    assert await manager.get_pivot_data("role-1") == {"is_primary": True}


@pytest.mark.asyncio
async def test_sync_attaches_and_detaches() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)
    await manager.attach("role-1")
    await manager.attach("role-2")

    await manager.sync(["role-2", "role-3"], {"role-3": {"is_primary": True}})

    assert await manager.get_attached_ids() == ["role-2", "role-3"]


@pytest.mark.asyncio
async def test_attach_requires_pivot_table() -> None:
    ds = _PivotDataSource()
    manager = _RolesManager(parent_id="p")
    manager.set_data_source(ds)

    with pytest.raises(RelationPersistenceError):
        await manager.attach("role-1")


@pytest.mark.asyncio
async def test_attach_requires_data_source() -> None:
    manager = _manager()  # pivot_table set, no data source

    with pytest.raises(RelationPersistenceError):
        await manager.attach("role-1")
