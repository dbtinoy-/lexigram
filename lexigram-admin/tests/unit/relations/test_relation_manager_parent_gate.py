"""Base-manager parent gate tests for relation managers (D2)."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.exceptions import PermissionDeniedError
from lexigram.admin.relations import AbstractRelationManager
from lexigram.result import Err


class _BaseRelationManager(AbstractRelationManager):
    relationship_name = "pets"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return []


class _DenyViewParentManager(_BaseRelationManager):
    def can_view_parent(self, parent: Any, user: Any | None = None) -> Any:
        return Err(PermissionDeniedError("denied"))


class _FakeDataSource:
    def __init__(self, parent: Any) -> None:
        self._parent = parent

    async def find_one(self, parent_id: Any) -> Any:
        return self._parent if parent_id == 7 else None


class _ResolvingParentManager(_BaseRelationManager):
    def __init__(
        self, parent_id: Any = None, data_source: _FakeDataSource | None = None
    ) -> None:
        super().__init__(parent_id=parent_id)
        self._resolver = data_source

    async def get_parent(self) -> Any:
        if self._resolver is None:
            return None
        return await self._resolver.find_one(self.parent_id)


class TestCanViewParent:
    def test_default_returns_ok(self) -> None:
        mgr = _BaseRelationManager(parent_id=1)
        result = mgr.can_view_parent(parent=object())
        assert result.is_ok()

    def test_override_denies(self) -> None:
        mgr = _DenyViewParentManager(parent_id=1)
        result = mgr.can_view_parent(parent=object())
        assert result.is_err()
        assert isinstance(result.unwrap_err(), PermissionDeniedError)


class TestGetParent:
    @pytest.mark.asyncio
    async def test_default_returns_declared_parent(self) -> None:
        parent = object()
        mgr = _BaseRelationManager(parent_id=1, parent=parent)
        assert await mgr.get_parent() is parent

    @pytest.mark.asyncio
    async def test_default_without_parent_returns_none(self) -> None:
        mgr = _BaseRelationManager(parent_id=1)
        assert await mgr.get_parent() is None

    @pytest.mark.asyncio
    async def test_override_resolves_through_data_source(self) -> None:
        parent = object()
        mgr = _ResolvingParentManager(parent_id=7, data_source=_FakeDataSource(parent))
        assert await mgr.get_parent() is parent

    @pytest.mark.asyncio
    async def test_override_missing_parent_returns_none(self) -> None:
        mgr = _ResolvingParentManager(
            parent_id=99, data_source=_FakeDataSource(object())
        )
        assert await mgr.get_parent() is None
