"""Unit tests for DynamoDBBackend and DynamoDBCollection."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub aioboto3 before importing anything from the backend so that the lazy
# `import aioboto3` inside connect() succeeds during tests without the real
# package being installed.
# ---------------------------------------------------------------------------

_aioboto3_stub = MagicMock()
sys.modules.setdefault("aioboto3", _aioboto3_stub)

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus  # noqa: E402
from lexigram.contracts.data.nosql.nosql import BulkWriteResult, DocumentResult  # noqa: E402
from lexigram.nosql.backends.dynamodb.backend import DynamoDBBackend  # noqa: E402
from lexigram.nosql.backends.dynamodb.collection import DynamoDBCollection  # noqa: E402
from lexigram.nosql.config import DynamoDBConfig  # noqa: E402
from lexigram.nosql.exceptions import DuplicateKeyError, NoSQLConnectionError, NoSQLError  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**kwargs: Any) -> DynamoDBConfig:
    """Return a DynamoDBConfig with sensible test defaults."""
    return DynamoDBConfig(
        table_name=kwargs.get("table_name", "test_table"),
        region=kwargs.get("region", "us-east-1"),
        access_key=kwargs.get("access_key", None),
        secret_key=kwargs.get("secret_key", None),
        endpoint_url=kwargs.get("endpoint_url", None),
        pk_field=kwargs.get("pk_field", "_id"),
    )


def _make_table_mock() -> MagicMock:
    """Return a fully mocked aioboto3 DynamoDB Table resource."""
    table = MagicMock()
    table.put_item = AsyncMock(return_value={})
    table.get_item = AsyncMock(return_value={"Item": None})
    table.scan = AsyncMock(return_value={"Items": []})
    table.update_item = AsyncMock(return_value={})
    table.delete_item = AsyncMock(return_value={})
    table.load = AsyncMock(return_value=None)

    # batch_writer is an async context manager
    batch_ctx = MagicMock()
    batch_ctx.__aenter__ = AsyncMock(return_value=batch_ctx)
    batch_ctx.__aexit__ = AsyncMock(return_value=False)
    batch_ctx.put_item = AsyncMock(return_value={})
    batch_ctx.delete_item = AsyncMock(return_value={})
    table.batch_writer = MagicMock(return_value=batch_ctx)

    # meta.client.exceptions.ConditionalCheckFailedException
    exc_cls = type("ConditionalCheckFailedException", (Exception,), {})
    table.meta = MagicMock()
    table.meta.client.exceptions.ConditionalCheckFailedException = exc_cls
    return table


async def _make_connected_backend(config: DynamoDBConfig | None = None) -> DynamoDBBackend:
    """Create a DynamoDBBackend that is already connected (aioboto3 mocked)."""
    cfg = config or _make_config()
    backend = DynamoDBBackend(cfg)

    # Build resource mock whose Table() coroutine returns a table mock.
    table_mock = _make_table_mock()
    resource_mock = MagicMock()
    resource_mock.Table = AsyncMock(return_value=table_mock)

    # resource context manager
    resource_ctx = MagicMock()
    resource_ctx.__aenter__ = AsyncMock(return_value=resource_mock)
    resource_ctx.__aexit__ = AsyncMock(return_value=False)

    # session.resource(...) returns the context manager
    session_mock = MagicMock()
    session_mock.resource = MagicMock(return_value=resource_ctx)

    aioboto3_mock = MagicMock()
    aioboto3_mock.Session = MagicMock(return_value=session_mock)

    with patch.dict(sys.modules, {"aioboto3": aioboto3_mock}):
        with patch(
            "lexigram.nosql.backends.dynamodb.backend.DynamoDBBackend._probe_connectivity",
            new_callable=AsyncMock,
        ):
            await backend.connect()

    # Attach resource for assertions
    backend._resource = resource_mock  # type: ignore[attr-defined]
    backend._resource_context = resource_ctx  # type: ignore[attr-defined]
    return backend


# ---------------------------------------------------------------------------
# Tests: DynamoDBBackend lifecycle
# ---------------------------------------------------------------------------


class TestDynamoDBBackendConnect:
    """Tests for DynamoDBBackend.connect() / disconnect() lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_sets_connected_flag(self) -> None:
        backend = await _make_connected_backend()
        assert backend.is_connected() is True

    @pytest.mark.asyncio
    async def test_connect_raises_when_aioboto3_missing(self) -> None:
        """connect() must raise NoSQLConnectionError when aioboto3 is absent."""
        cfg = _make_config()
        backend = DynamoDBBackend(cfg)

        # Temporarily hide aioboto3 from modules
        real = sys.modules.pop("aioboto3", None)
        try:
            with pytest.raises(NoSQLConnectionError, match="aioboto3 is required"):
                await backend.connect()
        finally:
            if real is not None:
                sys.modules["aioboto3"] = real

    @pytest.mark.asyncio
    async def test_disconnect_clears_state(self) -> None:
        backend = await _make_connected_backend()
        resource_ctx_mock = backend._resource_context  # type: ignore[attr-defined]
        resource_ctx_mock.__aexit__ = AsyncMock(return_value=False)

        await backend.disconnect()

        assert backend._resource is None  # type: ignore[attr-defined]
        assert backend.is_connected() is False

    @pytest.mark.asyncio
    async def test_disconnect_noop_when_not_connected(self) -> None:
        """disconnect() on a fresh backend must not raise."""
        cfg = _make_config()
        backend = DynamoDBBackend(cfg)
        backend._resource = None  # type: ignore[attr-defined]
        await backend.disconnect()  # should not raise

    @pytest.mark.asyncio
    async def test_connect_uses_explicit_credentials(self) -> None:
        """Explicit access_key / secret_key are forwarded to aioboto3.Session."""
        cfg = _make_config(access_key="AKID", secret_key="SECRET")
        backend = DynamoDBBackend(cfg)

        session_mock = MagicMock()
        resource_ctx = MagicMock()
        resource_mock = MagicMock()
        resource_mock.Table = AsyncMock(return_value=_make_table_mock())
        resource_ctx.__aenter__ = AsyncMock(return_value=resource_mock)
        resource_ctx.__aexit__ = AsyncMock(return_value=False)
        session_mock.resource = MagicMock(return_value=resource_ctx)

        aioboto3_mock = MagicMock()
        aioboto3_mock.Session = MagicMock(return_value=session_mock)

        with patch.dict(sys.modules, {"aioboto3": aioboto3_mock}):
            with patch(
                "lexigram.nosql.backends.dynamodb.backend.DynamoDBBackend._probe_connectivity",
                new_callable=AsyncMock,
            ):
                await backend.connect()

        aioboto3_mock.Session.assert_called_once_with(
            aws_access_key_id="AKID",
            aws_secret_access_key="SECRET",
        )

    @pytest.mark.asyncio
    async def test_connect_passes_endpoint_url(self) -> None:
        """endpoint_url is forwarded to session.resource(...)."""
        cfg = _make_config(endpoint_url="http://localhost:8000")
        backend = DynamoDBBackend(cfg)

        session_mock = MagicMock()
        resource_ctx = MagicMock()
        resource_mock = MagicMock()
        resource_mock.Table = AsyncMock(return_value=_make_table_mock())
        resource_ctx.__aenter__ = AsyncMock(return_value=resource_mock)
        resource_ctx.__aexit__ = AsyncMock(return_value=False)
        session_mock.resource = MagicMock(return_value=resource_ctx)

        aioboto3_mock = MagicMock()
        aioboto3_mock.Session = MagicMock(return_value=session_mock)

        with patch.dict(sys.modules, {"aioboto3": aioboto3_mock}):
            with patch(
                "lexigram.nosql.backends.dynamodb.backend.DynamoDBBackend._probe_connectivity",
                new_callable=AsyncMock,
            ):
                await backend.connect()

        session_mock.resource.assert_called_once_with(
            "dynamodb",
            region_name="us-east-1",
            endpoint_url="http://localhost:8000",
        )


# ---------------------------------------------------------------------------
# Tests: DynamoDBBackend.collection()
# ---------------------------------------------------------------------------


class TestDynamoDBBackendCollection:
    """Tests for collection() factory and caching."""

    @pytest.mark.asyncio
    async def test_collection_returns_dynamodb_collection(self) -> None:
        backend = await _make_connected_backend()
        col = backend.collection("users")
        assert isinstance(col, DynamoDBCollection)

    @pytest.mark.asyncio
    async def test_collection_caches_by_name(self) -> None:
        backend = await _make_connected_backend()
        col_a = backend.collection("orders")
        col_b = backend.collection("orders")
        assert col_a is col_b

    @pytest.mark.asyncio
    async def test_collection_different_names_are_distinct(self) -> None:
        backend = await _make_connected_backend()
        assert backend.collection("a") is not backend.collection("b")

    @pytest.mark.asyncio
    async def test_collection_raises_when_not_connected(self) -> None:
        cfg = _make_config()
        backend = DynamoDBBackend(cfg)
        with pytest.raises(RuntimeError, match="not connected"):
            backend.collection("users")


# ---------------------------------------------------------------------------
# Tests: DynamoDBBackend.health_check()
# ---------------------------------------------------------------------------


class TestDynamoDBBackendHealthCheck:
    """Tests for health_check()."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self) -> None:
        backend = await _make_connected_backend()
        with patch.object(backend, "_probe_connectivity", new_callable=AsyncMock):
            result = await backend.health_check()

        assert isinstance(result, HealthCheckResult)
        assert result.component == "dynamodb"
        assert result.status == HealthStatus.HEALTHY
        assert result.details is not None
        assert result.details["region"] == "us-east-1"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_when_probe_fails(self) -> None:
        backend = await _make_connected_backend()

        async def _fail() -> None:
            raise RuntimeError("DynamoDB unreachable")

        with patch.object(backend, "_probe_connectivity", side_effect=_fail):
            result = await backend.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Health check failed" in (result.message or "")

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_when_not_connected(self) -> None:
        cfg = _make_config()
        backend = DynamoDBBackend(cfg)
        result = await backend.health_check()
        assert result.status == HealthStatus.UNHEALTHY
        assert result.component == "dynamodb"


# ---------------------------------------------------------------------------
# Tests: DynamoDBCollection — helpers
# ---------------------------------------------------------------------------


def _make_collection(
    table: MagicMock | None = None,
    name: str = "items",
    pk_field: str = "_id",
) -> DynamoDBCollection:
    return DynamoDBCollection(
        table=table or _make_table_mock(),
        name=name,
        pk_field=pk_field,
    )


# ---------------------------------------------------------------------------
# Tests: DynamoDBCollection.insert_one()
# ---------------------------------------------------------------------------


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


class TestExports:
    """Verify that DynamoDBBackend and DynamoDBConfig are reachable via __init__."""

    def test_dynamodb_backend_importable_from_backends(self) -> None:
        from lexigram.nosql.backends import DynamoDBBackend as _DDB

        assert _DDB is DynamoDBBackend

    def test_dynamodb_config_importable_from_nosql(self) -> None:
        from lexigram.nosql import DynamoDBConfig as _Cfg  # type: ignore[attr-defined]

        assert _Cfg is DynamoDBConfig


# ---------------------------------------------------------------------------
# Tests: DynamoDBBackend additional coverage
# ---------------------------------------------------------------------------


class TestDynamoDBBackendProbe:
    """Tests for _probe_connectivity failure paths."""

    @pytest.mark.asyncio
    async def test_connect_raises_on_probe_failure(self) -> None:
        """When _probe_connectivity raises, connect() must raise NoSQLConnectionError."""
        cfg = _make_config()
        backend = DynamoDBBackend(cfg)
        resource_mock = MagicMock()
        resource_ctx = MagicMock()
        resource_ctx.__aenter__ = AsyncMock(return_value=resource_mock)
        resource_ctx.__aexit__ = AsyncMock(return_value=False)
        session_mock = MagicMock()
        session_mock.resource = MagicMock(return_value=resource_ctx)
        aioboto3_mock = MagicMock()
        aioboto3_mock.Session = MagicMock(return_value=session_mock)

        with patch.dict(sys.modules, {"aioboto3": aioboto3_mock}):
            with patch.object(
                backend, "_probe_connectivity",
                side_effect=NoSQLConnectionError("table not found"),
            ):
                with pytest.raises(NoSQLConnectionError, match="table not found"):
                    await backend.connect()

        assert backend._resource is None


class TestDynamoDBBackendDisconnect:
    """Tests for disconnect() edge cases."""

    @pytest.mark.asyncio
    async def test_disconnect_swallows_close_error(self) -> None:
        """disconnect() must not raise when __aexit__ fails."""
        backend = await _make_connected_backend()
        resource_ctx = backend._resource_context  # type: ignore[attr-defined]
        resource_ctx.__aexit__ = AsyncMock(side_effect=RuntimeError("close error"))

        await backend.disconnect()  # should not raise
        assert backend._resource is None
        assert backend.is_connected() is False


class TestDynamoDBBackendSession:
    """Tests for session() method."""

    @pytest.mark.asyncio
    async def test_session_returns_noop_context_manager(self) -> None:
        backend = await _make_connected_backend()
        async with backend.session():
            pass  # noop — should not raise


class TestDynamoDBBackendListCollections:
    """Tests for list_collections()."""

    @pytest.mark.asyncio
    async def test_list_collections_returns_names(self) -> None:
        backend = await _make_connected_backend()
        paginator = MagicMock()
        paginator.paginate.return_value.__aiter__.return_value = [
            {"TableNames": ["users", "orders"]},
            {"TableNames": ["products"]},
        ]
        backend._resource.meta.client.get_paginator.return_value = paginator  # type: ignore[attr-defined]

        names = await backend.list_collections()
        assert names == ["users", "orders", "products"]

    @pytest.mark.asyncio
    async def test_list_collections_raises_when_not_connected(self) -> None:
        cfg = _make_config()
        backend = DynamoDBBackend(cfg)
        with pytest.raises(RuntimeError, match="not connected"):
            await backend.list_collections()


class TestDynamoDBBackendDropCollection:
    """Tests for drop_collection()."""

    @pytest.mark.asyncio
    async def test_drop_collection_truncates_table(self) -> None:
        backend = await _make_connected_backend()
        table = MagicMock()
        table.load = AsyncMock()
        table.key_schema = [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ]
        table.scan = AsyncMock(
            return_value={
                "Items": [{"pk": "1", "sk": "a"}, {"pk": "2", "sk": "b"}],
            }
        )
        batch = MagicMock()
        batch.__aenter__ = AsyncMock(return_value=batch)
        batch.__aexit__ = AsyncMock(return_value=False)
        batch.delete_item = AsyncMock()
        table.batch_writer.return_value = batch
        backend._resource.Table = AsyncMock(return_value=table)

        await backend.drop_collection("my_table")

        assert table.scan.await_count >= 1
        assert batch.delete_item.await_count == 2

    @pytest.mark.asyncio
    async def test_drop_collection_with_pagination(self) -> None:
        backend = await _make_connected_backend()
        table = MagicMock()
        table.load = AsyncMock()
        table.key_schema = [
            {"AttributeName": "pk", "KeyType": "HASH"},
        ]
        table.scan = AsyncMock(
            side_effect=[
                {
                    "Items": [{"pk": "1"}, {"pk": "2"}],
                    "LastEvaluatedKey": {"pk": "2"},
                },
                {"Items": [{"pk": "3"}]},
            ]
        )
        batch = MagicMock()
        batch.__aenter__ = AsyncMock(return_value=batch)
        batch.__aexit__ = AsyncMock(return_value=False)
        batch.delete_item = AsyncMock()
        table.batch_writer.return_value = batch
        backend._resource.Table = AsyncMock(return_value=table)

        await backend.drop_collection("big_table")

        assert table.scan.await_count == 2
        assert batch.delete_item.await_count == 3

    @pytest.mark.asyncio
    async def test_drop_collection_raises_when_not_connected(self) -> None:
        cfg = _make_config()
        backend = DynamoDBBackend(cfg)
        with pytest.raises(RuntimeError, match="not connected"):
            await backend.drop_collection("test")


class TestDynamoDBBackendHealthCheckProbe:
    """Tests for health_check() probe failure path."""

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_probe_exception(self) -> None:
        backend = await _make_connected_backend()

        async def _fail() -> None:
            raise RuntimeError("probe error")

        with patch.object(backend, "_probe_connectivity", side_effect=_fail):
            result = await backend.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Health check failed" in (result.message or "")


class TestDynamoDBBackendHealthCheckNotConnected:
    """Tests for health_check() when not connected."""

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_no_resource(self) -> None:
        backend = DynamoDBBackend(_make_config())
        result = await backend.health_check()
        assert result.status == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# Tests: _DeferredDynamoDBCollection
# ---------------------------------------------------------------------------


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
