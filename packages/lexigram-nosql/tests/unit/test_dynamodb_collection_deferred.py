"""Deferred (lazy-resolution) DynamoDB collection tests."""

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


class TestDeferredDynamoDBCollection:
    """Tests for _DeferredDynamoDBCollection lazy table resolution."""

    @pytest.mark.asyncio
    async def test_ensure_table_resolves_lazily(self) -> None:
        from lexigram.nosql.backends.dynamodb.backend import _DeferredDynamoDBCollection

        resource = MagicMock()
        table = MagicMock()
        resource.Table = AsyncMock(return_value=table)

        col = _DeferredDynamoDBCollection(resource=resource, name="items")
        assert col._table_resolved is False

        await col._ensure_table()
        assert col._table_resolved is True
        resource.Table.assert_awaited_once_with("items")

    @pytest.mark.asyncio
    async def test_insert_one_ensures_table(self) -> None:
        from lexigram.nosql.backends.dynamodb.backend import _DeferredDynamoDBCollection

        resource = MagicMock()
        table = _make_table_mock()
        resource.Table = AsyncMock(return_value=table)

        col = _DeferredDynamoDBCollection(resource=resource, name="items")
        await col.insert_one({"_id": "x"})
        assert col._table_resolved is True

    @pytest.mark.asyncio
    async def test_insert_many_ensures_table(self) -> None:
        from lexigram.nosql.backends.dynamodb.backend import _DeferredDynamoDBCollection

        resource = MagicMock()
        table = _make_table_mock()
        resource.Table = AsyncMock(return_value=table)

        col = _DeferredDynamoDBCollection(resource=resource, name="items")
        await col.insert_many([{"_id": "a"}, {"_id": "b"}])
        assert col._table_resolved is True

    @pytest.mark.asyncio
    async def test_find_one_ensures_table(self) -> None:
        from lexigram.nosql.backends.dynamodb.backend import _DeferredDynamoDBCollection

        resource = MagicMock()
        table = _make_table_mock()
        resource.Table = AsyncMock(return_value=table)

        col = _DeferredDynamoDBCollection(resource=resource, name="items")
        result = await col.find_one({"_id": "x"})
        assert col._table_resolved is True

    @pytest.mark.asyncio
    async def test_find_ensures_table(self) -> None:
        from lexigram.nosql.backends.dynamodb.backend import _DeferredDynamoDBCollection

        resource = MagicMock()
        table = _make_table_mock()
        resource.Table = AsyncMock(return_value=table)

        col = _DeferredDynamoDBCollection(resource=resource, name="items")
        _ = [doc async for doc in await col.find({})]
        assert col._table_resolved is True

    @pytest.mark.asyncio
    async def test_update_one_ensures_table(self) -> None:
        from lexigram.nosql.backends.dynamodb.backend import _DeferredDynamoDBCollection

        resource = MagicMock()
        table = _make_table_mock()
        resource.Table = AsyncMock(return_value=table)

        col = _DeferredDynamoDBCollection(resource=resource, name="items")
        await col.update_one({"_id": "x"}, {"name": "X"})
        assert col._table_resolved is True

    @pytest.mark.asyncio
    async def test_update_many_ensures_table(self) -> None:
        from lexigram.nosql.backends.dynamodb.backend import _DeferredDynamoDBCollection

        resource = MagicMock()
        table = _make_table_mock()
        resource.Table = AsyncMock(return_value=table)

        col = _DeferredDynamoDBCollection(resource=resource, name="items")
        await col.update_many({"_id": "x"}, {"name": "X"})
        assert col._table_resolved is True

    @pytest.mark.asyncio
    async def test_delete_one_ensures_table(self) -> None:
        from lexigram.nosql.backends.dynamodb.backend import _DeferredDynamoDBCollection

        resource = MagicMock()
        table = _make_table_mock()
        resource.Table = AsyncMock(return_value=table)

        col = _DeferredDynamoDBCollection(resource=resource, name="items")
        await col.delete_one({"_id": "x"})
        assert col._table_resolved is True

    @pytest.mark.asyncio
    async def test_delete_many_ensures_table(self) -> None:
        from lexigram.nosql.backends.dynamodb.backend import _DeferredDynamoDBCollection

        resource = MagicMock()
        table = _make_table_mock()
        resource.Table = AsyncMock(return_value=table)

        col = _DeferredDynamoDBCollection(resource=resource, name="items")
        await col.delete_many({"_id": "x"})
        assert col._table_resolved is True

    @pytest.mark.asyncio
    async def test_count_documents_ensures_table(self) -> None:
        from lexigram.nosql.backends.dynamodb.backend import _DeferredDynamoDBCollection

        resource = MagicMock()
        table = _make_table_mock()
        resource.Table = AsyncMock(return_value=table)

        col = _DeferredDynamoDBCollection(resource=resource, name="items")
        await col.count_documents({})
        assert col._table_resolved is True
