"""Repository-level guard tests: injected payloads never reach the driver (4.5)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.nosql.backends.mongodb.collection import MongoDBCollection
from lexigram.nosql.exceptions import NoSQLFilterError
from lexigram.nosql.repository.base import DocumentRepository


class _UserRepository(DocumentRepository[dict[str, Any], str]):
    """Minimal repository over raw documents."""

    collection_name = "users"
    id_field = "_id"

    async def _document_to_entity(self, document: dict[str, Any]) -> dict[str, Any]:
        return document

    async def _entity_to_document(self, entity: dict[str, Any]) -> dict[str, Any]:
        return entity


@pytest.fixture
def repo() -> tuple[_UserRepository, MagicMock]:
    motor_col = MagicMock()
    cursor = AsyncMock()
    cursor.__aiter__.return_value = []
    cursor.sort = MagicMock(return_value=cursor)
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    motor_col.find = MagicMock(return_value=cursor)
    store = MagicMock()
    store.collection.return_value = MongoDBCollection(motor_col)
    return _UserRepository(store), motor_col


class TestRepositoryGuard:
    """Injected payloads raise at the guarded collection, never the driver."""

    @pytest.mark.asyncio
    async def test_find_by_filter_where_rejected(
        self,
        repo: tuple[_UserRepository, MagicMock],
    ) -> None:
        repository, motor_col = repo

        with pytest.raises(NoSQLFilterError):
            await repository.find_by_filter({"$where": "return true"})

        motor_col.find.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_unsafe_regex_rejected(
        self,
        repo: tuple[_UserRepository, MagicMock],
    ) -> None:
        repository, motor_col = repo

        with pytest.raises(NoSQLFilterError):
            await repository.list(active={"$regex": "a;b"})

        motor_col.find.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_by_filter_safe_reaches_driver(
        self,
        repo: tuple[_UserRepository, MagicMock],
    ) -> None:
        repository, motor_col = repo

        result = await repository.find_by_filter({"status": "active"})

        assert result == []
        motor_col.find.assert_called_once_with({"status": "active"}, projection=None)

    @pytest.mark.asyncio
    async def test_list_gated_regex_reaches_driver(
        self,
        repo: tuple[_UserRepository, MagicMock],
    ) -> None:
        repository, motor_col = repo

        await repository.list(active={"$regex": "^J", "$options": "i"})

        motor_col.find.assert_called_once_with(
            {"active": {"$regex": "^J", "$options": "i"}},
            projection=None,
        )

    @pytest.mark.asyncio
    async def test_list_ne_nested_passes(
        self,
        repo: tuple[_UserRepository, MagicMock],
    ) -> None:
        repository, motor_col = repo

        await repository.list(status={"$ne": "deleted"})

        motor_col.find.assert_called_once_with(
            {"status": {"$ne": "deleted"}},
            projection=None,
        )