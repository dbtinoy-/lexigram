"""Tests for the relation actions (associate/attach/detach/dissociate)."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.relation import (
    AssociateAction,
    AttachAction,
    DetachAction,
    DissociateAction,
)
from lexigram.admin.actions.types import ActionColor, ActionContext
from lexigram.admin.relations.belongs_to_many import BelongsToManyRelationManager


class _PivotDataSource:
    """In-memory pivot data source."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self._next_id = 1

    async def find_many(self, query: Any) -> Any:
        return _QueryResult(list(self.rows))

    async def create(self, data: dict[str, Any]) -> Any:
        self.rows.append({**data, "id": self._next_id})
        self._next_id += 1
        return self.rows[-1]

    async def bulk_delete(self, ids: list[Any]) -> int:
        self.rows = [r for r in self.rows if r["id"] not in ids]
        return len(ids)

    async def update(self, item_id: Any, data: dict[str, Any]) -> Any:
        for row in self.rows:
            if row["id"] == item_id:
                row.update(data)
                return row
        return None


class _QueryResult:
    def __init__(self, items: list[Any]) -> None:
        self.items = items
        self.total = len(items)


class _RolesManager(BelongsToManyRelationManager):
    async def get_query(self) -> list[Any]:
        return []


class _NoDetachManager:
    """Relation manager without a detach operation."""


def _manager(ds: _PivotDataSource | None = None) -> _RolesManager:
    manager = _RolesManager(parent_id="parent-1")
    manager.pivot_table = "user_roles"
    if ds is not None:
        manager.set_data_source(ds)
    return manager


def _ctx(**metadata: Any) -> ActionContext:
    return ActionContext(metadata=metadata)


@pytest.mark.asyncio
async def test_associate_attaches_via_metadata_manager() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)
    ctx = _ctx(relation_manager=manager)

    result = await AssociateAction().execute({"id": "role-1"}, ctx)

    assert result.is_ok()
    payload = result.unwrap()
    assert payload["action"] == "associate"
    assert payload["related_id"] == "role-1"
    assert ds.rows[0]["parent_id"] == "parent-1"
    assert ds.rows[0]["related_id"] == "role-1"


@pytest.mark.asyncio
async def test_associate_uses_ctor_manager_and_related_id() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)
    action = AssociateAction(relation_manager=manager, related_id="role-9")

    result = await action.execute(None, _ctx())

    assert result.is_ok()
    assert result.unwrap()["related_id"] == "role-9"
    assert ds.rows[0]["related_id"] == "role-9"


@pytest.mark.asyncio
async def test_associate_missing_manager_returns_err() -> None:
    result = await AssociateAction().execute({"id": "role-1"}, ActionContext())

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ActionError)


@pytest.mark.asyncio
async def test_associate_missing_related_id_returns_err() -> None:
    manager = _manager(_PivotDataSource())
    result = await AssociateAction(relation_manager=manager).execute(None, _ctx())

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ActionError)


@pytest.mark.asyncio
async def test_associate_rejects_non_pivot_manager() -> None:
    result = await AssociateAction(relation_manager=_NoDetachManager()).execute(
        {"id": "x"}, _ctx()
    )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ActionError)


@pytest.mark.asyncio
async def test_attach_uses_associate_execution() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)
    action = AttachAction(relation_manager=manager)
    assert action.name == "attach"
    assert action.label == "Attach"
    assert action.icon == "link"
    assert action.color == ActionColor.PRIMARY

    result = await action.execute({"id": "role-1"}, _ctx())

    assert result.is_ok()
    assert result.unwrap()["action"] == "associate"
    assert ds.rows[0]["related_id"] == "role-1"


@pytest.mark.asyncio
async def test_detach_removes_pivot_row() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)
    await manager.attach("role-1")
    await manager.attach("role-2")
    action = DetachAction(relation_manager=manager)
    assert action.label == "Detach"

    result = await action.execute({"id": "role-1"}, _ctx())

    assert result.is_ok()
    assert result.unwrap()["action"] == "detach"
    assert await manager.get_attached_ids() == ["role-2"]


@pytest.mark.asyncio
async def test_detach_rejects_non_pivot_manager() -> None:
    result = await DetachAction(relation_manager=_NoDetachManager()).execute(
        {"id": "x"}, _ctx()
    )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ActionError)


@pytest.mark.asyncio
async def test_dissociate_detaches_via_pivot_manager() -> None:
    ds = _PivotDataSource()
    manager = _manager(ds)
    await manager.attach("role-1")
    action = DissociateAction(relation_manager=manager)

    result = await action.execute({"id": "role-1"}, _ctx())

    assert result.is_ok()
    assert result.unwrap()["action"] == "dissociate"
    assert await manager.get_attached_ids() == []


@pytest.mark.asyncio
async def test_dissociate_requires_detach_capability() -> None:
    result = await DissociateAction(relation_manager=_NoDetachManager()).execute(
        {"id": "x"}, _ctx()
    )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ActionError)


@pytest.mark.asyncio
async def test_dissociate_missing_manager_returns_err() -> None:
    result = await DissociateAction().execute({"id": "x"}, ActionContext())

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ActionError)
