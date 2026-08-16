from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.data.nosql.nosql import BulkWriteResult, DocumentResult
from lexigram.nosql.backends.mongodb.collection import MongoDBCollection
from lexigram.nosql.exceptions import DuplicateKeyError, NoSQLError


class TestMongoDBCollection:
    """Tests for MongoDBCollection."""

    @pytest.fixture
    def motor_col(self) -> MagicMock:
        col = MagicMock()
        col.name = "test_collection"
        return col

    @pytest.fixture
    def col(self, motor_col: MagicMock) -> MongoDBCollection:
        return MongoDBCollection(motor_col)

    def test_name(self, col: MongoDBCollection) -> None:
        assert col.name == "test_collection"

    # ── Insert One ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_insert_one_returns_document_result(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        result = MagicMock()
        result.inserted_id = "abc123"
        result.acknowledged = True
        motor_col.insert_one = AsyncMock(return_value=result)

        doc_result = await col.insert_one({"name": "Alice"})

        assert isinstance(doc_result, DocumentResult)
        assert doc_result.document_id == "abc123"
        assert doc_result.acknowledged is True

    @pytest.mark.asyncio
    async def test_insert_one_duplicate_key(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        from pymongo.errors import DuplicateKeyError as _DKE

        motor_col.insert_one = AsyncMock(
            side_effect=_DKE("E11000 duplicate key")
        )

        with pytest.raises(DuplicateKeyError):
            await col.insert_one({"name": "Alice"})

    @pytest.mark.asyncio
    async def test_insert_one_wraps_generic_error(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        from pymongo.errors import PyMongoError as _PME

        motor_col.insert_one = AsyncMock(
            side_effect=_PME("connection lost")
        )

        with pytest.raises(NoSQLError, match="insert_one failed"):
            await col.insert_one({"name": "Alice"})

    # ── Insert Many ─────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_insert_many_returns_bulk_write_result(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        result = MagicMock()
        result.inserted_ids = ["id1", "id2"]
        motor_col.insert_many = AsyncMock(return_value=result)

        bulk = await col.insert_many([{"a": 1}, {"b": 2}])

        assert isinstance(bulk, BulkWriteResult)
        assert bulk.inserted_count == 2
        assert bulk.upserted_ids == ["id1", "id2"]

    @pytest.mark.asyncio
    async def test_insert_many_duplicate_key(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        from pymongo.errors import DuplicateKeyError as _DKE

        motor_col.insert_many = AsyncMock(
            side_effect=_DKE("E11000 duplicate key")
        )

        with pytest.raises(DuplicateKeyError):
            await col.insert_many([{"a": 1}])

    @pytest.mark.asyncio
    async def test_insert_many_wraps_error(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        from pymongo.errors import PyMongoError as _PME

        motor_col.insert_many = AsyncMock(
            side_effect=_PME("batch fail")
        )

        with pytest.raises(NoSQLError, match="insert_many failed"):
            await col.insert_many([{"a": 1}])

    # ── Find One ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_find_one_returns_document(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_col.find_one = AsyncMock(return_value={"_id": "abc", "name": "Alice"})

        doc = await col.find_one({"_id": "abc"})
        assert doc == {"_id": "abc", "name": "Alice"}

    @pytest.mark.asyncio
    async def test_find_one_returns_none(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_col.find_one = AsyncMock(return_value=None)

        doc = await col.find_one({"_id": "missing"})
        assert doc is None

    @pytest.mark.asyncio
    async def test_find_one_passes_projection(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_col.find_one = AsyncMock(return_value={"name": "Alice"})

        await col.find_one({"_id": "abc"}, projection={"name": 1})

        motor_col.find_one.assert_awaited_once_with({"_id": "abc"}, projection={"name": 1})

    # ── Find ────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_find_yields_documents(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        cursor = AsyncMock()
        cursor.__aiter__.return_value = [{"_id": "1"}, {"_id": "2"}]
        motor_col.find = MagicMock(return_value=cursor)

        results = [doc async for doc in col.find({})]

        assert len(results) == 2
        motor_col.find.assert_called_once_with({}, projection=None)

    @pytest.mark.asyncio
    async def test_find_with_sort_skip_limit(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        cursor = AsyncMock()
        cursor.__aiter__.return_value = [{"_id": "1"}]
        cursor.sort = MagicMock(return_value=cursor)
        cursor.skip = MagicMock(return_value=cursor)
        cursor.limit = MagicMock(return_value=cursor)
        motor_col.find = MagicMock(return_value=cursor)

        results = [doc async for doc in col.find({}, sort=[("name", 1)], skip=5, limit=10)]

        assert len(results) == 1
        cursor.sort.assert_called_once_with([("name", 1)])
        cursor.skip.assert_called_once_with(5)
        cursor.limit.assert_called_once_with(10)

    # ── Update ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_update_one_returns_document_result(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        result = MagicMock()
        result.matched_count = 1
        result.modified_count = 1
        result.upserted_id = None
        result.acknowledged = True
        motor_col.update_one = AsyncMock(return_value=result)

        dr = await col.update_one({"_id": "1"}, {"$set": {"name": "Bob"}})

        assert isinstance(dr, DocumentResult)
        assert dr.matched_count == 1
        assert dr.modified_count == 1

    @pytest.mark.asyncio
    async def test_update_one_with_upsert(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        result = MagicMock()
        result.matched_count = 0
        result.modified_count = 0
        result.upserted_id = "new_id"
        result.acknowledged = True
        motor_col.update_one = AsyncMock(return_value=result)

        dr = await col.update_one({"_id": "1"}, {"$set": {"name": "Bob"}}, upsert=True)

        assert dr.upserted_id == "new_id"

    @pytest.mark.asyncio
    async def test_update_many(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        result = MagicMock()
        result.matched_count = 3
        result.modified_count = 3
        result.acknowledged = True
        motor_col.update_many = AsyncMock(return_value=result)

        dr = await col.update_many({"status": "active"}, {"$set": {"flag": True}})

        assert dr.matched_count == 3
        assert dr.modified_count == 3

    # ── Delete ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_one(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        result = MagicMock()
        result.deleted_count = 1
        result.acknowledged = True
        motor_col.delete_one = AsyncMock(return_value=result)

        dr = await col.delete_one({"_id": "1"})
        assert dr.matched_count == 1

    @pytest.mark.asyncio
    async def test_delete_many(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        result = MagicMock()
        result.deleted_count = 5
        result.acknowledged = True
        motor_col.delete_many = AsyncMock(return_value=result)

        dr = await col.delete_many({"status": "obsolete"})
        assert dr.matched_count == 5

    # ── Replace One ─────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_replace_one(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        result = MagicMock()
        result.matched_count = 1
        result.modified_count = 1
        result.upserted_id = None
        result.acknowledged = True
        motor_col.replace_one = AsyncMock(return_value=result)

        dr = await col.replace_one({"_id": "1"}, {"name": "Charlie"})
        assert dr.matched_count == 1

    @pytest.mark.asyncio
    async def test_replace_one_upsert(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        result = MagicMock()
        result.matched_count = 0
        result.modified_count = 0
        result.upserted_id = "new_id"
        result.acknowledged = True
        motor_col.replace_one = AsyncMock(return_value=result)

        dr = await col.replace_one({"_id": "1"}, {"name": "Charlie"}, upsert=True)

        assert dr.upserted_id == "new_id"

    # ── Find One And Update ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_find_one_and_update(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_col.find_one_and_update = AsyncMock(
            return_value={"_id": "1", "name": "Updated"}
        )

        result = await col.find_one_and_update({"_id": "1"}, {"$set": {"name": "Updated"}})

        assert result is not None
        assert result["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_find_one_and_update_return_before(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_col.find_one_and_update = AsyncMock(
            return_value={"_id": "1", "name": "Before"}
        )

        result = await col.find_one_and_update(
            {"_id": "1"}, {"$set": {"name": "After"}}, return_document=False
        )

        assert result is not None
        assert result["name"] == "Before"

    @pytest.mark.asyncio
    async def test_find_one_and_update_returns_none(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_col.find_one_and_update = AsyncMock(return_value=None)

        result = await col.find_one_and_update({"_id": "missing"}, {"$set": {"n": 1}})
        assert result is None

    # ── Count and Index ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_count_documents(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_col.count_documents = AsyncMock(return_value=42)

        count = await col.count_documents({"active": True})
        assert count == 42

    @pytest.mark.asyncio
    async def test_count_documents_no_filter(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_col.count_documents = AsyncMock(return_value=100)

        count = await col.count_documents()
        assert count == 100

    @pytest.mark.asyncio
    async def test_create_index(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_col.create_index = AsyncMock(return_value="email_1")

        name = await col.create_index([("email", 1)], unique=True, name="email_1")

        assert name == "email_1"
        motor_col.create_index.assert_awaited_once_with([("email", 1)], unique=True, name="email_1")

    @pytest.mark.asyncio
    async def test_create_index_no_name(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_col.create_index = AsyncMock(return_value="email_1")

        name = await col.create_index([("email", 1)])

        motor_col.create_index.assert_awaited_once_with([("email", 1)], unique=False)

    # ── Aggregate ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_aggregate_yields_documents(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        cursor = AsyncMock()
        cursor.__aiter__.return_value = [{"_id": "1"}, {"_id": "2"}]
        motor_col.aggregate = MagicMock(return_value=cursor)

        results = [doc async for doc in col.aggregate([{"$match": {}}])]

        assert len(results) == 2

    # ── List Indexes ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_list_indexes(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        cursor = AsyncMock()
        cursor.__aiter__.return_value = [{"name": "_id_"}, {"name": "email_1"}]
        motor_col.list_indexes = MagicMock(return_value=cursor)

        indexes = await col.list_indexes()
        assert len(indexes) == 2

    # ── Distinct ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_distinct(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_col.distinct = AsyncMock(return_value=["a", "b", "c"])

        values = await col.distinct("status", {"active": True})
        assert values == ["a", "b", "c"]

    # ── Bulk Write ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_bulk_write_empty(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        result = await col.bulk_write([])
        assert isinstance(result, BulkWriteResult)
        assert result.inserted_count == 0

    @pytest.mark.asyncio
    async def test_bulk_write(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_result = MagicMock()
        motor_result.inserted_count = 2
        motor_result.matched_count = 3
        motor_result.modified_count = 1
        motor_result.deleted_count = 0
        motor_result.upserted_ids = {"0": "u1", "1": "u2"}
        motor_col.bulk_write = AsyncMock(return_value=motor_result)

        result = await col.bulk_write([MagicMock(), MagicMock()])

        assert result.inserted_count == 2
        assert result.matched_count == 3
        assert result.modified_count == 1
        assert result.deleted_count == 0
        assert result.upserted_ids == ["u1", "u2"]

    @pytest.mark.asyncio
    async def test_bulk_write_no_upserted_ids(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        motor_result = MagicMock()
        motor_result.inserted_count = 0
        motor_result.matched_count = 1
        motor_result.modified_count = 0
        motor_result.deleted_count = 0
        motor_result.upserted_ids = None
        motor_col.bulk_write = AsyncMock(return_value=motor_result)

        result = await col.bulk_write([MagicMock()])

        assert result.upserted_ids == []

    @pytest.mark.asyncio
    async def test_bulk_write_raises_nosql_error(self, col: MongoDBCollection, motor_col: MagicMock) -> None:
        from pymongo.errors import PyMongoError as _PME

        motor_col.bulk_write = AsyncMock(
            side_effect=_PME("write concern error")
        )

        with pytest.raises(NoSQLError, match="bulk_write failed"):
            await col.bulk_write([MagicMock()])
