"""Tests for DocumentRepository with mocked collection."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.data.nosql.nosql import DocumentResult
from lexigram.nosql.repository.base import DocumentRepository


class _User:
    """Test entity."""

    def __init__(self, id: str | None = None, name: str = "", email: str = "") -> None:
        self.id = id
        self.name = name
        self.email = email


class UserRepository(DocumentRepository[_User, str]):
    """Test repository for _User entities."""

    collection_name = "users"
    id_field = "_id"

    async def _document_to_entity(self, document: dict[str, Any]) -> _User:
        return _User(id=document.get("_id"), name=document.get("name", ""), email=document.get("email", ""))

    async def _entity_to_document(self, entity: _User) -> dict[str, Any]:
        doc: dict[str, Any] = {"name": entity.name, "email": entity.email}
        if entity.id:
            doc["_id"] = entity.id
        return doc


def _make_mock_store() -> MagicMock:
    """Create a mock DocumentStoreProtocol."""
    store = MagicMock()
    collection = MagicMock()
    store.collection.return_value = collection
    return store


class TestDocumentRepository:
    """Tests for the base document repository."""

    @pytest.mark.asyncio
    async def test_get_existing(self) -> None:
        store = _make_mock_store()
        col = store.collection.return_value
        col.find_one = AsyncMock(return_value={"_id": "u1", "name": "Alice", "email": "a@x.com"})

        repo = UserRepository(store)
        user = await repo.get("u1")

        assert user is not None
        assert user.id == "u1"
        assert user.name == "Alice"
        col.find_one.assert_awaited_once_with({"_id": "u1"})

    @pytest.mark.asyncio
    async def test_get_missing(self) -> None:
        store = _make_mock_store()
        col = store.collection.return_value
        col.find_one = AsyncMock(return_value=None)

        repo = UserRepository(store)
        user = await repo.get("missing")

        assert user is None

    @pytest.mark.asyncio
    async def test_save_new(self) -> None:
        store = _make_mock_store()
        col = store.collection.return_value
        col.insert_one = AsyncMock(return_value=DocumentResult(document_id="new-id"))

        repo = UserRepository(store)
        user = await repo.save(_User(name="Bob", email="b@x.com"))

        assert user.id == "new-id"
        col.insert_one.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_existing(self) -> None:
        store = _make_mock_store()
        col = store.collection.return_value
        col.update_one = AsyncMock(return_value=DocumentResult(modified_count=1))

        repo = UserRepository(store)
        user = await repo.save(_User(id="u1", name="Bob", email="b@x.com"))

        assert user.name == "Bob"
        col.update_one.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_hard(self) -> None:
        store = _make_mock_store()
        col = store.collection.return_value
        col.delete_one = AsyncMock(return_value=DocumentResult(matched_count=1))

        repo = UserRepository(store)
        result = await repo.delete("u1")

        assert result is True
        col.delete_one.assert_awaited_once_with({"_id": "u1"})

    @pytest.mark.asyncio
    async def test_delete_soft(self) -> None:
        store = _make_mock_store()
        col = store.collection.return_value
        col.update_one = AsyncMock(return_value=DocumentResult(modified_count=1))

        repo = UserRepository(store, soft_delete=True)
        result = await repo.delete("u1")

        assert result is True
        col.update_one.assert_awaited_once()
        call_args = col.update_one.call_args
        assert call_args[0][0] == {"_id": "u1"}
        assert "$set" in call_args[0][1]
        assert call_args[0][1]["$set"]["_deleted"] is True

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        store = _make_mock_store()
        col = store.collection.return_value
        col.count_documents = AsyncMock(return_value=42)

        repo = UserRepository(store)
        count = await repo.count(status="active")

        assert count == 42
        col.count_documents.assert_awaited_once_with({"status": "active"})

    @pytest.mark.asyncio
    async def test_count_soft_delete_filters(self) -> None:
        store = _make_mock_store()
        col = store.collection.return_value
        col.count_documents = AsyncMock(return_value=10)

        repo = UserRepository(store, soft_delete=True)
        await repo.count()

        call_args = col.count_documents.call_args[0][0]
        assert "_deleted" in call_args
        assert call_args["_deleted"] == {"$ne": True}

    @pytest.mark.asyncio
    async def test_save_many(self) -> None:
        store = _make_mock_store()
        col = store.collection.return_value
        col.insert_many = AsyncMock()

        repo = UserRepository(store)
        users = [_User(name="A", email="a@x.com"), _User(name="B", email="b@x.com")]
        result = await repo.save_many(users)

        assert len(result) == 2
        col.insert_many.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_many(self) -> None:
        store = _make_mock_store()
        col = store.collection.return_value
        col.delete_many = AsyncMock(return_value=DocumentResult(matched_count=3))

        repo = UserRepository(store)
        count = await repo.delete_many(["u1", "u2", "u3"])

        assert count == 3
        col.delete_many.assert_awaited_once()


class TestDocumentRepositoryConfig:
    """Tests for config functionality."""

    def test_config_defaults(self) -> None:
        from lexigram.nosql.config import NoSQLConfig

        config = NoSQLConfig()
        assert config.driver == "mongodb"
        assert config.enabled is True
        assert config.mongodb.database == "lexigram"
        assert config.mongodb.max_pool_size == 100

    def test_mongodb_config_defaults(self) -> None:
        from lexigram.nosql.config import MongoDBConfig

        config = MongoDBConfig()
        assert config.uri == "mongodb://localhost:27017"
        assert config.retry_writes is True
        assert config.read_preference == "primaryPreferred"
