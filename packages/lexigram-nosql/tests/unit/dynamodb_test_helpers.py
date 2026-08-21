"""Shared doubles/factories for DynamoDB backend and collection tests."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from lexigram.nosql.backends.dynamodb.backend import DynamoDBBackend
from lexigram.nosql.backends.dynamodb.collection import DynamoDBCollection
from lexigram.nosql.config import DynamoDBConfig


# ---------------------------------------------------------------------------
# Stub aioboto3 before importing anything from the backend so that the lazy
# `import aioboto3` inside connect() succeeds during tests without the real
# package being installed.
# ---------------------------------------------------------------------------

_aioboto3_stub = MagicMock()
sys.modules.setdefault("aioboto3", _aioboto3_stub)


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
