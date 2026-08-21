"""DynamoDBBackend lifecycle, health, and export tests."""

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


