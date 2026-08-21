"""DynamoDBCollection CRUD tests."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dynamodb_test_helpers import (
    _make_collection,
    _make_config,
    _make_connected_backend,
    _make_table_mock,
)

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.data.nosql.nosql import BulkWriteResult, DocumentResult
from lexigram.nosql.backends.dynamodb.backend import DynamoDBBackend
from lexigram.nosql.backends.dynamodb.collection import DynamoDBCollection
from lexigram.nosql.config import DynamoDBConfig
from lexigram.nosql.exceptions import DuplicateKeyError, NoSQLConnectionError, NoSQLError


class TestDynamoDBCollectionInsertOne:
    """Tests for DynamoDBCollection.insert_one()."""

    @pytest.mark.asyncio
    async def test_insert_one_returns_document_result(self) -> None:
        col = _make_collection()
        result = await col.insert_one({"_id": "abc", "name": "Alice"})
        assert isinstance(result, DocumentResult)
        assert result.document_id == "abc"
        assert result.acknowledged is True

    @pytest.mark.asyncio
    async def test_insert_one_generates_id_when_missing(self) -> None:
        col = _make_collection()
        result = await col.insert_one({"name": "Bob"})
        assert result.document_id is not None
        assert len(result.document_id) == 36  # UUID4

    @pytest.mark.asyncio
    async def test_insert_one_calls_put_item(self) -> None:
        table = _make_table_mock()
        col = _make_collection(table=table)
        await col.insert_one({"_id": "x1", "val": 1})
        table.put_item.assert_awaited_once()
        call_kwargs = table.put_item.call_args.kwargs
        assert call_kwargs["Item"]["_id"] == "x1"
        assert "ConditionExpression" in call_kwargs

    @pytest.mark.asyncio
    async def test_insert_one_raises_duplicate_key_error(self) -> None:
        table = _make_table_mock()
        exc_cls = table.meta.client.exceptions.ConditionalCheckFailedException
        table.put_item = AsyncMock(side_effect=exc_cls("already exists"))
        col = _make_collection(table=table)
        with pytest.raises(DuplicateKeyError):
            await col.insert_one({"_id": "dup"})

    @pytest.mark.asyncio
    async def test_insert_one_wraps_generic_exception(self) -> None:
        table = _make_table_mock()
        table.put_item = AsyncMock(side_effect=RuntimeError("boom"))
        col = _make_collection(table=table)
        with pytest.raises(NoSQLError):
            await col.insert_one({"_id": "err"})


# ---------------------------------------------------------------------------
# Tests: DynamoDBCollection.insert_many()
# ---------------------------------------------------------------------------


class TestDynamoDBCollectionInsertMany:
    """Tests for DynamoDBCollection.insert_many()."""

    @pytest.mark.asyncio
    async def test_insert_many_returns_bulk_write_result(self) -> None:
        col = _make_collection()
        result = await col.insert_many([{"_id": "1"}, {"_id": "2"}])
        assert isinstance(result, BulkWriteResult)
        assert result.inserted_count == 2

    @pytest.mark.asyncio
    async def test_insert_many_empty_returns_zero(self) -> None:
        col = _make_collection()
        result = await col.insert_many([])
        assert result.inserted_count == 0

    @pytest.mark.asyncio
    async def test_insert_many_uses_batch_writer(self) -> None:
        table = _make_table_mock()
        col = _make_collection(table=table)
        await col.insert_many([{"_id": "a"}, {"_id": "b"}, {"_id": "c"}])
        table.batch_writer.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_many_generates_ids_for_missing(self) -> None:
        col = _make_collection()
        result = await col.insert_many([{}, {}])
        assert result.inserted_count == 2
        assert all(len(uid) == 36 for uid in result.upserted_ids)


# ---------------------------------------------------------------------------
# Tests: DynamoDBCollection.find_one()
# ---------------------------------------------------------------------------


class TestDynamoDBCollectionFindOne:
    """Tests for DynamoDBCollection.find_one()."""

    @pytest.mark.asyncio
    async def test_find_one_by_pk_uses_get_item(self) -> None:
        table = _make_table_mock()
        table.get_item = AsyncMock(return_value={"Item": {"_id": "u1", "name": "Alice"}})
        col = _make_collection(table=table)

        doc = await col.find_one({"_id": "u1"})

        table.get_item.assert_awaited_once_with(Key={"_id": "u1"})
        assert doc is not None
        assert doc["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_find_one_by_pk_returns_none_when_missing(self) -> None:
        table = _make_table_mock()
        table.get_item = AsyncMock(return_value={})
        col = _make_collection(table=table)
        doc = await col.find_one({"_id": "ghost"})
        assert doc is None

    @pytest.mark.asyncio
    async def test_find_one_non_pk_uses_scan(self) -> None:
        table = _make_table_mock()
        table.scan = AsyncMock(
            return_value={"Items": [{"_id": "u2", "name": "Bob"}]}
        )
        col = _make_collection(table=table)

        doc = await col.find_one({"name": "Bob"})

        table.scan.assert_awaited()
        assert doc is not None
        assert doc["_id"] == "u2"

    @pytest.mark.asyncio
    async def test_find_one_non_pk_returns_none_when_no_match(self) -> None:
        table = _make_table_mock()
        table.scan = AsyncMock(return_value={"Items": []})
        col = _make_collection(table=table)
        doc = await col.find_one({"name": "Ghost"})
        assert doc is None


# ---------------------------------------------------------------------------
# Tests: DynamoDBCollection.find()
# ---------------------------------------------------------------------------


class TestDynamoDBCollectionFind:
    """Tests for DynamoDBCollection.find()."""

    @pytest.mark.asyncio
    async def test_find_yields_all_items(self) -> None:
        table = _make_table_mock()
        table.scan = AsyncMock(
            return_value={"Items": [{"_id": "1"}, {"_id": "2"}, {"_id": "3"}]}
        )
        col = _make_collection(table=table)
        results = [doc async for doc in await col.find({})]
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_find_with_filter_passes_filter_expression(self) -> None:
        table = _make_table_mock()
        table.scan = AsyncMock(return_value={"Items": [{"_id": "x", "status": "active"}]})
        col = _make_collection(table=table)

        results = [doc async for doc in await col.find({"status": "active"})]

        call_kwargs = table.scan.call_args.kwargs
        assert "FilterExpression" in call_kwargs
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_find_paginates_last_evaluated_key(self) -> None:
        table = _make_table_mock()
        table.scan = AsyncMock(
            side_effect=[
                {"Items": [{"_id": "p1"}], "LastEvaluatedKey": {"_id": "p1"}},
                {"Items": [{"_id": "p2"}]},
            ]
        )
        col = _make_collection(table=table)
        results = [doc async for doc in await col.find({})]
        assert len(results) == 2
        assert table.scan.await_count == 2

    @pytest.mark.asyncio
    async def test_find_applies_limit(self) -> None:
        table = _make_table_mock()
        table.scan = AsyncMock(
            return_value={"Items": [{"_id": str(i)} for i in range(10)]}
        )
        col = _make_collection(table=table)
        results = [doc async for doc in await col.find({}, limit=3)]
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_find_applies_skip(self) -> None:
        table = _make_table_mock()
        table.scan = AsyncMock(
            return_value={"Items": [{"_id": str(i)} for i in range(5)]}
        )
        col = _make_collection(table=table)
        results = [doc async for doc in await col.find({}, skip=2)]
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_find_raises_nosql_error_on_failure(self) -> None:
        table = _make_table_mock()
        table.scan = AsyncMock(side_effect=RuntimeError("scan failed"))
        col = _make_collection(table=table)
        with pytest.raises(NoSQLError):
            async for _ in await col.find({}):
                pass


# ---------------------------------------------------------------------------
# Tests: DynamoDBCollection.update_one()
# ---------------------------------------------------------------------------


class TestDynamoDBCollectionUpdateOne:
    """Tests for DynamoDBCollection.update_one()."""

    @pytest.mark.asyncio
    async def test_update_one_returns_document_result(self) -> None:
        table = _make_table_mock()
        table.get_item = AsyncMock(
            return_value={"Item": {"_id": "u1", "name": "Alice"}}
        )
        col = _make_collection(table=table)
        result = await col.update_one({"_id": "u1"}, {"name": "Alicia"})
        assert isinstance(result, DocumentResult)
        assert result.matched_count == 1
        assert result.modified_count == 1

    @pytest.mark.asyncio
    async def test_update_one_returns_zero_matched_when_not_found(self) -> None:
        table = _make_table_mock()
        table.get_item = AsyncMock(return_value={})
        col = _make_collection(table=table)
        result = await col.update_one({"_id": "ghost"}, {"name": "X"})
        assert result.matched_count == 0

    @pytest.mark.asyncio
    async def test_update_one_upserts_when_flag_set(self) -> None:
        table = _make_table_mock()
        table.get_item = AsyncMock(return_value={})
        col = _make_collection(table=table)
        result = await col.update_one({"_id": "new"}, {"_id": "new", "name": "Y"}, upsert=True)
        assert result.upserted_id is not None

    @pytest.mark.asyncio
    async def test_update_one_calls_update_item(self) -> None:
        table = _make_table_mock()
        table.get_item = AsyncMock(
            return_value={"Item": {"_id": "u1", "name": "Alice"}}
        )
        col = _make_collection(table=table)
        await col.update_one({"_id": "u1"}, {"name": "Alicia"})
        table.update_item.assert_awaited_once()
        call_kwargs = table.update_item.call_args.kwargs
        assert call_kwargs["Key"] == {"_id": "u1"}
        assert "UpdateExpression" in call_kwargs


# ---------------------------------------------------------------------------
# Tests: DynamoDBCollection.delete_one()
# ---------------------------------------------------------------------------


class TestDynamoDBCollectionDeleteOne:
    """Tests for DynamoDBCollection.delete_one()."""

    @pytest.mark.asyncio
    async def test_delete_one_returns_document_result(self) -> None:
        table = _make_table_mock()
        table.get_item = AsyncMock(
            return_value={"Item": {"_id": "d1", "name": "Alice"}}
        )
        col = _make_collection(table=table)
        result = await col.delete_one({"_id": "d1"})
        assert isinstance(result, DocumentResult)
        assert result.matched_count == 1

    @pytest.mark.asyncio
    async def test_delete_one_returns_zero_when_not_found(self) -> None:
        table = _make_table_mock()
        table.get_item = AsyncMock(return_value={})
        col = _make_collection(table=table)
        result = await col.delete_one({"_id": "ghost"})
        assert result.matched_count == 0

    @pytest.mark.asyncio
    async def test_delete_one_calls_delete_item(self) -> None:
        table = _make_table_mock()
        table.get_item = AsyncMock(
            return_value={"Item": {"_id": "d1"}}
        )
        col = _make_collection(table=table)
        await col.delete_one({"_id": "d1"})
        table.delete_item.assert_awaited_once_with(Key={"_id": "d1"})


# ---------------------------------------------------------------------------
# Tests: DynamoDBCollection.count_documents()
# ---------------------------------------------------------------------------


class TestDynamoDBCollectionCount:
    """Tests for DynamoDBCollection.count_documents()."""

    @pytest.mark.asyncio
    async def test_count_returns_total_when_no_filter(self) -> None:
        table = _make_table_mock()
        table.scan = AsyncMock(
            return_value={"Items": [{"_id": str(i)} for i in range(7)]}
        )
        col = _make_collection(table=table)
        count = await col.count_documents()
        assert count == 7

    @pytest.mark.asyncio
    async def test_count_with_filter(self) -> None:
        table = _make_table_mock()
        table.scan = AsyncMock(
            return_value={"Items": [{"_id": "1", "active": True}, {"_id": "2", "active": True}]}
        )
        col = _make_collection(table=table)
        count = await col.count_documents({"active": True})
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_returns_zero_for_empty_table(self) -> None:
        table = _make_table_mock()
        table.scan = AsyncMock(return_value={"Items": []})
        col = _make_collection(table=table)
        count = await col.count_documents()
        assert count == 0


# ---------------------------------------------------------------------------
# Tests: exports
# ---------------------------------------------------------------------------


