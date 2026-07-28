"""DynamoDB document store backend."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger
from lexigram.nosql.backends.base import AbstractDocumentStore
from lexigram.nosql.backends.dynamodb.collection import DynamoDBCollection
from lexigram.nosql.exceptions import NoSQLConnectionError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from contextlib import AbstractAsyncContextManager

    from lexigram.nosql.config import DynamoDBConfig

logger = get_logger(__name__)


class DynamoDBBackend(AbstractDocumentStore):
    """Async DynamoDB document store backend built on aioboto3.

    Each call to :meth:`collection` returns a :class:`DynamoDBCollection`
    that wraps an aioboto3 DynamoDB ``Table`` resource.  Because DynamoDB
    is a single-table-per-resource model, each logical collection maps to
    a separate DynamoDB table.

    Features:

    - Async table operations via ``aioboto3`` DynamoDB resource
    - Configurable region, endpoint URL (LocalStack support), and
      optional explicit AWS credentials
    - ``scan``-based find with equality ``FilterExpression``
    - Batch writes (``batch_writer``) for ``insert_many``
    - Health check via ``describe_table`` on the configured default table
    - No-op session context (DynamoDB transactions are managed via
      ``TransactWriteItems`` / ``TransactGetItems`` at the SDK level)

    Usage::

        backend = DynamoDBBackend(config)
        await backend.connect()
        users = backend.collection("users")
        await users.insert_one({"name": "Alice"})
        await backend.disconnect()

    Args:
        config: :class:`~lexigram.nosql.config.DynamoDBConfig` instance.
    """

    def __init__(self, config: DynamoDBConfig) -> None:
        super().__init__(database_name=config.table_name)
        self._config = config
        self._session: Any = None
        self._resource: Any = None

    # ──────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Initialise the aioboto3 DynamoDB resource and verify connectivity."""
        try:
            import aioboto3  # type: ignore[import-not-found]
        except ImportError as exc:
            raise NoSQLConnectionError(
                "aioboto3 is required for DynamoDB support. "
                "Install with: pip install lexigram-nosql[dynamodb]"
            ) from exc

        session_kwargs: dict[str, Any] = {}
        if self._config.access_key:
            session_kwargs["aws_access_key_id"] = self._config.access_key
        if self._config.secret_key:
            session_kwargs["aws_secret_access_key"] = self._config.secret_key

        resource_kwargs: dict[str, Any] = {
            "region_name": self._config.region,
        }
        if self._config.endpoint_url:
            resource_kwargs["endpoint_url"] = self._config.endpoint_url

        self._session = aioboto3.Session(**session_kwargs)
        self._resource_context = self._session.resource("dynamodb", **resource_kwargs)
        self._resource = await self._resource_context.__aenter__()

        # Verify connectivity with a lightweight describe_table on the
        # default table.  This validates credentials and network access
        # without scanning any data.
        try:
            await asyncio.wait_for(
                self._probe_connectivity(),
                timeout=10.0,
            )
        except NoSQLConnectionError:
            await self._resource_context.__aexit__(None, None, None)
            self._resource = None
            raise
        except Exception as exc:
            await self._resource_context.__aexit__(None, None, None)
            self._resource = None
            raise NoSQLConnectionError(
                f"DynamoDB connectivity check failed for table "
                f"{self._config.table_name!r} in region {self._config.region!r}: {exc}"
            ) from exc

        self._connected = True
        logger.info(
            "nosql.dynamodb.connected",
            table=self._config.table_name,
            region=self._config.region,
            endpoint=self._config.endpoint_url or "aws",
        )

    async def _probe_connectivity(self) -> None:
        """Issue a ``describe_table`` on the default table to verify connectivity.

        Raises:
            :class:`~lexigram.nosql.exceptions.NoSQLConnectionError`: If
                the table does not exist or credentials are invalid.
        """
        try:
            table = await self._resource.Table(self._config.table_name)
            await table.load()
        except Exception as exc:
            raise NoSQLConnectionError(
                f"DynamoDB describe_table failed for {self._config.table_name!r}: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """Close the aioboto3 DynamoDB resource."""
        if self._resource is not None:
            try:
                await self._resource_context.__aexit__(None, None, None)
            except Exception as exc:  # noqa: BLE001  # aioboto3 close may raise on already-closed session
                logger.debug("nosql.dynamodb.close_error", error=str(exc))
            finally:
                self._resource = None
                self._collections.clear()
                self._connected = False
            logger.info(
                "nosql.dynamodb.disconnected",
                table=self._config.table_name,
            )

    # ──────────────────────────────────────────────────────────────
    # Collection access
    # ──────────────────────────────────────────────────────────────

    def _create_collection(self, name: str) -> DynamoDBCollection:  # type: ignore[override]
        """Return a :class:`DynamoDBCollection` for the DynamoDB table *name*.

        Args:
            name: DynamoDB table name.

        Returns:
            :class:`DynamoDBCollection` bound to the table.

        Raises:
            RuntimeError: If not connected.
        """
        if self._resource is None:
            raise RuntimeError(
                "DynamoDBBackend is not connected. Call connect() first."
            )
        # aioboto3 Table resources are lazy — no network call is made here.
        # The actual table object is created asynchronously on first use.
        # We store the factory callable so the collection can create the
        # Table resource when it needs it.
        return _DeferredDynamoDBCollection(
            resource=self._resource,
            name=name,
            pk_field=self._config.pk_field,
        )

    # ──────────────────────────────────────────────────────────────
    # Session (no-op: DynamoDB transactions are managed externally)
    # ──────────────────────────────────────────────────────────────

    @asynccontextmanager
    async def _noop_session(self) -> AsyncIterator[None]:
        yield

    def session(self) -> AbstractAsyncContextManager:
        """Return a no-op async context manager.

        DynamoDB transactional writes require ``TransactWriteItems`` at the
        SDK level, which is beyond the scope of this abstract session API.
        """
        return self._noop_session()

    # ──────────────────────────────────────────────────────────────
    # Collection listing / dropping
    # ──────────────────────────────────────────────────────────────

    async def list_collections(self) -> list[str]:
        """List DynamoDB table names visible in the current AWS account/region.

        Returns:
            List of table names.

        Raises:
            RuntimeError: If not connected.
        """
        if self._resource is None:
            raise RuntimeError(
                "DynamoDBBackend is not connected. Call connect() first."
            )
        client = self._resource.meta.client
        names: list[str] = []
        paginator = client.get_paginator("list_tables")
        async for page in paginator.paginate():
            names.extend(page.get("TableNames", []))
        return names

    async def drop_collection(self, name: str) -> None:
        """Delete all items in the DynamoDB table *name*.

        Note:
            DynamoDB has no ``TRUNCATE TABLE``.  This method scans all
            items and deletes them in batches of 25.  For large tables,
            consider deleting and recreating the table instead.

        Args:
            name: Table name to truncate.

        Raises:
            RuntimeError: If not connected.
        """
        if self._resource is None:
            raise RuntimeError(
                "DynamoDBBackend is not connected. Call connect() first."
            )
        table = await self._resource.Table(name)
        # Determine the partition key name from the table's key schema.
        await table.load()
        key_schema = table.key_schema or []
        pk_attr = next(
            (k["AttributeName"] for k in key_schema if k["KeyType"] == "HASH"),
            "_id",
        )
        sk_attr = next(
            (k["AttributeName"] for k in key_schema if k["KeyType"] == "RANGE"),
            None,
        )

        response = await table.scan(
            ProjectionExpression=pk_attr if not sk_attr else f"{pk_attr}, {sk_attr}"
        )
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = await table.scan(
                ProjectionExpression=pk_attr
                if not sk_attr
                else f"{pk_attr}, {sk_attr}",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        async with table.batch_writer() as batch:
            for item in items:
                key = {pk_attr: item[pk_attr]}
                if sk_attr and sk_attr in item:
                    key[sk_attr] = item[sk_attr]
                await batch.delete_item(Key=key)

        self._collections.pop(name, None)
        logger.info("nosql.dynamodb.collection_dropped", table=name, deleted=len(items))

    # ──────────────────────────────────────────────────────────────
    # Health check
    # ──────────────────────────────────────────────────────────────

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Verify DynamoDB connectivity via a ``describe_table`` probe.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            :class:`~lexigram.contracts.core.HealthCheckResult`.
        """
        if not self._resource or not self._connected:
            return HealthCheckResult(
                component="dynamodb",
                status=HealthStatus.UNHEALTHY,
                message="Not connected",
            )
        try:
            await asyncio.wait_for(
                self._probe_connectivity(),
                timeout=timeout,
            )
            return HealthCheckResult(
                component="dynamodb",
                status=HealthStatus.HEALTHY,
                details={
                    "table": self._config.table_name,
                    "region": self._config.region,
                },
            )
        except TimeoutError:
            return HealthCheckResult(
                component="dynamodb",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {timeout}s",
            )
        except Exception as exc:  # noqa: BLE001  # health check must absorb all SDK errors
            return HealthCheckResult(
                component="dynamodb",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {exc}",
            )


class _DeferredDynamoDBCollection(DynamoDBCollection):
    """DynamoDBCollection that resolves its table resource on first access.

    aioboto3 ``Table`` resources must be obtained via ``await resource.Table(name)``
    which is a coroutine.  This subclass defers that call until the first
    operation so that :meth:`DynamoDBBackend._create_collection` can remain
    synchronous (as required by ``AbstractDocumentStore``).
    """

    def __init__(
        self,
        resource: Any,
        name: str,
        *,
        pk_field: str = "_id",
    ) -> None:
        # Pass a sentinel; the real table is resolved lazily.
        super().__init__(table=None, name=name, pk_field=pk_field)
        self._resource = resource
        self._table_resolved = False

    async def _ensure_table(self) -> None:
        """Resolve the aioboto3 Table resource if not already done."""
        if not self._table_resolved:
            self._table = await self._resource.Table(self._name)
            self._table_resolved = True

    # Override all public methods to inject the lazy-init guard.

    async def insert_one(self, document: dict[str, Any]) -> Any:
        await self._ensure_table()
        return await super().insert_one(document)

    async def insert_many(self, documents: list[dict[str, Any]]) -> Any:
        await self._ensure_table()
        return await super().insert_many(documents)

    async def find_one(
        self,
        filter: dict[str, Any],  # noqa: A002
        *,
        projection: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        await self._ensure_table()
        return await super().find_one(filter, projection=projection)

    async def find(
        self,
        filter: dict[str, Any],  # noqa: A002
        *,
        projection: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        skip: int = 0,
        limit: int = 0,
    ) -> Any:
        await self._ensure_table()
        return await super().find(
            filter, projection=projection, sort=sort, skip=skip, limit=limit
        )

    async def update_one(
        self,
        filter: dict[str, Any],  # noqa: A002
        update: dict[str, Any],
        *,
        upsert: bool = False,
    ) -> Any:
        await self._ensure_table()
        return await super().update_one(filter, update, upsert=upsert)

    async def update_many(
        self,
        filter: dict[str, Any],  # noqa: A002
        update: dict[str, Any],
    ) -> Any:
        await self._ensure_table()
        return await super().update_many(filter, update)

    async def delete_one(self, filter: dict[str, Any]) -> Any:  # noqa: A002
        await self._ensure_table()
        return await super().delete_one(filter)

    async def delete_many(self, filter: dict[str, Any]) -> Any:  # noqa: A002
        await self._ensure_table()
        return await super().delete_many(filter)

    async def count_documents(self, filter: dict[str, Any] | None = None) -> int:  # noqa: A002
        await self._ensure_table()
        return await super().count_documents(filter)


__all__ = ["DynamoDBBackend"]
