"""Tests for Resource.duplicate() lifecycle hooks.

Verifies that Resource.duplicate() correctly fetches a record,
applies before_clone / after_clone hooks, and delegates to the
data source for the actual create.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.resources.base import Resource


class _ClonableResource(Resource):
    """Concrete Resource subclass for testing clone behavior."""


class _FakeDataSource:
    """Minimal IDataSource implementation for testing."""

    def __init__(self) -> None:
        self.find_one = AsyncMock(
            return_value={"id": 1, "name": "Original", "email": "test@example.com"}
        )
        self.create = AsyncMock(
            return_value={
                "id": 2,
                "name": "Original (Copy)",
                "email": "test@example.com",
            }
        )
        self.find_many = AsyncMock()

    async def count(self, query: object = None) -> int:
        return 0

    async def update(self, item_id: object, data: dict) -> object:
        return data

    async def delete(self, item_id: object) -> bool:
        return True

    async def bulk_create(self, items: list) -> list:
        return items

    async def bulk_update(self, items: list) -> list:
        return items

    async def bulk_delete(self, item_ids: list) -> int:
        return len(item_ids)


class TestResourceDuplicate:
    """Tests for Resource.duplicate()."""

    @pytest.fixture
    def mock_data_source(self) -> _FakeDataSource:
        return _FakeDataSource()

    @pytest.fixture
    def resource(self, mock_data_source: MagicMock) -> _ClonableResource:
        res = _ClonableResource()
        res.set_data_source(mock_data_source)
        return res

    @pytest.mark.asyncio
    async def test_duplicate_creates_copy(
        self,
        resource: _ClonableResource,
        mock_data_source: MagicMock,
    ) -> None:
        """Verify duplicate(1) fetches the record and creates a copy."""
        record = await resource.duplicate(1)

        mock_data_source.find_one.assert_awaited_once_with(1)
        mock_data_source.create.assert_awaited_once()

        created_data = mock_data_source.create.call_args[0][0]
        assert "id" not in created_data
        assert created_data["name"] == "Original (Copy)"
        assert record == {
            "id": 2,
            "name": "Original (Copy)",
            "email": "test@example.com",
        }

    @pytest.mark.asyncio
    async def test_before_clone_modifies_data(
        self,
        resource: _ClonableResource,
        mock_data_source: MagicMock,
    ) -> None:
        """Override before_clone and verify the modified data reaches create."""

        async def custom_before(data: dict[str, Any]) -> dict[str, Any]:
            data["name"] = "Customized Copy"
            data["source"] = "cloned"
            return data

        resource.before_clone = custom_before  # type: ignore[method-assign]

        await resource.duplicate(1)

        created_data = mock_data_source.create.call_args[0][0]
        assert created_data["name"] == "Customized Copy"
        assert created_data["source"] == "cloned"

    @pytest.mark.asyncio
    async def test_after_clone_is_called(
        self,
        resource: _ClonableResource,
        mock_data_source: MagicMock,
    ) -> None:
        """Override after_clone and verify it receives the created record."""
        after_clone_called = False
        cloned_record: Any = None

        async def custom_after(record: Any) -> None:
            nonlocal after_clone_called, cloned_record
            after_clone_called = True
            cloned_record = record

        resource.after_clone = custom_after  # type: ignore[method-assign]

        await resource.duplicate(1)

        assert after_clone_called
        assert cloned_record == {
            "id": 2,
            "name": "Original (Copy)",
            "email": "test@example.com",
        }

    @pytest.mark.asyncio
    async def test_duplicate_raises_without_data_source(self) -> None:
        """duplicate() raises RuntimeError when _data_source is None."""
        res = _ClonableResource()
        with pytest.raises(RuntimeError, match="No data source"):
            await res.duplicate(1)

    @pytest.mark.asyncio
    async def test_duplicate_missing_record_does_not_create_empty_copy(self) -> None:
        """Missing clone sources fail before before_clone/create run."""
        res = _ClonableResource()
        source = _FakeDataSource()
        source.find_one = AsyncMock(return_value=None)
        res.set_data_source(source)

        with pytest.raises(LookupError, match="not found"):
            await res.duplicate(999)

        source.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_duplicate_appends_copy_suffix(self) -> None:
        """Default before_clone strips 'id' and appends ' (Copy)' to name."""
        res = _ClonableResource()
        data = await res.before_clone({"id": 1, "name": "Original"})
        assert "id" not in data
        assert data["name"] == "Original (Copy)"

    @pytest.mark.asyncio
    async def test_before_clone_preserves_other_fields(self) -> None:
        """Default before_clone only strips 'id' and modifies 'name'."""
        res = _ClonableResource()
        data = await res.before_clone(
            {"id": 1, "name": "Original", "email": "test@example.com", "role": "admin"}
        )
        assert "id" not in data
        assert data["name"] == "Original (Copy)"
        assert data["email"] == "test@example.com"
        assert data["role"] == "admin"
