"""Tests for Resource.restore() and Resource.purge() lifecycle hooks.

Verifies that restore() and purge() correctly fetch records, apply
before/after hooks, and delegate to the data source appropriately.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.resources.base import Resource


class _SoftDeleteResource(Resource):
    """Concrete Resource subclass for testing soft-delete behavior."""


class _FakeDataSource:
    """Minimal IDataSource implementation for testing soft-delete operations.

    Exposes AsyncMock find_one, update, and delete so callers can
    assert invocation patterns and inspect passed arguments.
    """

    def __init__(self) -> None:
        self.find_one = AsyncMock(
            return_value={
                "id": 1,
                "name": "Deleted Record",
                "deleted_at": "2026-01-01T00:00:00",
            }
        )
        self.update = AsyncMock(
            return_value={"id": 1, "name": "Deleted Record", "deleted_at": None}
        )
        self.delete = AsyncMock(return_value=True)
        self.find_many = AsyncMock()

    async def create(self, data: dict) -> Any:
        return data

    async def count(self, query: object = None) -> int:
        return 0

    async def bulk_create(self, items: list) -> list:
        return items

    async def bulk_update(self, items: list) -> list:
        return items

    async def bulk_delete(self, item_ids: list) -> int:
        return len(item_ids)


class TestResourceRestore:
    """Tests for Resource.restore()."""

    @pytest.fixture
    def mock_data_source(self) -> _FakeDataSource:
        return _FakeDataSource()

    @pytest.fixture
    def resource(self, mock_data_source: MagicMock) -> _SoftDeleteResource:
        res = _SoftDeleteResource()
        res.set_data_source(mock_data_source)
        return res

    @pytest.mark.asyncio
    async def test_restore_unsets_deleted_at(
        self,
        resource: _SoftDeleteResource,
        mock_data_source: MagicMock,
    ) -> None:
        """Verify restore(1) calls data_source.update with deleted_at=None."""
        record = await resource.restore(1)

        mock_data_source.find_one.assert_awaited_once_with(1)
        mock_data_source.update.assert_awaited_once_with(1, {"deleted_at": None})
        assert record == {"id": 1, "name": "Deleted Record", "deleted_at": None}

    @pytest.mark.asyncio
    async def test_before_restore_modifies_data(
        self,
        resource: _SoftDeleteResource,
        mock_data_source: MagicMock,
    ) -> None:
        """Override before_restore and verify modified data reaches update."""

        async def custom_before(data: dict[str, Any]) -> dict[str, Any]:
            data["restored_by"] = "admin"
            data["deleted_at"] = None
            return data

        resource.before_restore = custom_before  # type: ignore[method-assign]

        await resource.restore(1)

        updated_data = mock_data_source.update.call_args[0][1]
        assert updated_data["deleted_at"] is None
        assert updated_data["restored_by"] == "admin"

    @pytest.mark.asyncio
    async def test_after_restore_is_called(
        self,
        resource: _SoftDeleteResource,
        mock_data_source: MagicMock,
    ) -> None:
        """Override after_restore and verify it receives the restored record."""
        after_restore_called = False
        restored_record: Any = None

        async def custom_after(record: Any) -> None:
            nonlocal after_restore_called, restored_record
            after_restore_called = True
            restored_record = record

        resource.after_restore = custom_after  # type: ignore[method-assign]

        await resource.restore(1)

        assert after_restore_called
        assert restored_record == {
            "id": 1,
            "name": "Deleted Record",
            "deleted_at": None,
        }

    @pytest.mark.asyncio
    async def test_restore_raises_without_data_source(self) -> None:
        """restore() raises RuntimeError when _data_source is None."""
        res = _SoftDeleteResource()
        with pytest.raises(RuntimeError, match="No data source"):
            await res.restore(1)


class TestResourcePurge:
    """Tests for Resource.purge()."""

    @pytest.fixture
    def mock_data_source(self) -> _FakeDataSource:
        return _FakeDataSource()

    @pytest.fixture
    def resource(self, mock_data_source: MagicMock) -> _SoftDeleteResource:
        res = _SoftDeleteResource()
        res.set_data_source(mock_data_source)
        return res

    @pytest.mark.asyncio
    async def test_purge_calls_delete(
        self,
        resource: _SoftDeleteResource,
        mock_data_source: MagicMock,
    ) -> None:
        """Verify purge(1) calls data_source.delete(1)."""
        await resource.purge(1)

        mock_data_source.find_one.assert_awaited_once_with(1)
        mock_data_source.delete.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_before_purge_modifies_data(
        self,
        resource: _SoftDeleteResource,
        mock_data_source: MagicMock,
    ) -> None:
        """Override before_purge and verify it receives the record data."""
        before_purge_data: Any = None

        async def custom_before(data: dict[str, Any]) -> dict[str, Any]:
            nonlocal before_purge_data
            before_purge_data = data
            return data

        resource.before_purge = custom_before  # type: ignore[method-assign]

        await resource.purge(1)

        assert before_purge_data == {
            "id": 1,
            "name": "Deleted Record",
            "deleted_at": "2026-01-01T00:00:00",
        }

    @pytest.mark.asyncio
    async def test_after_purge_is_called(
        self,
        resource: _SoftDeleteResource,
        mock_data_source: MagicMock,
    ) -> None:
        """Override after_purge and verify it's called with the item_id."""
        after_purge_called = False
        purged_id: Any = None

        async def custom_after(item_id: Any) -> None:
            nonlocal after_purge_called, purged_id
            after_purge_called = True
            purged_id = item_id

        resource.after_purge = custom_after  # type: ignore[method-assign]

        await resource.purge(1)

        assert after_purge_called
        assert purged_id == 1

    @pytest.mark.asyncio
    async def test_purge_raises_without_data_source(self) -> None:
        """purge() raises RuntimeError when _data_source is None."""
        res = _SoftDeleteResource()
        with pytest.raises(RuntimeError, match="No data source"):
            await res.purge(1)
