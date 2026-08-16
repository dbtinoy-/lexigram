"""MongoDB document store backend using motor async client."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

pymongo: Any
try:
    import pymongo as _pymongo

    pymongo = _pymongo
except ImportError:
    pymongo = None

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger
from lexigram.nosql.backends.base import AbstractDocumentStore
from lexigram.nosql.backends.mongodb.codecs import configure_codecs
from lexigram.nosql.backends.mongodb.collection import MongoDBCollection
from lexigram.nosql.backends.mongodb.session import mongodb_session
from lexigram.nosql.exceptions import NoSQLConnectionError

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from lexigram.nosql.config import MongoDBConfig

logger = get_logger(__name__)


class MongoDBDocumentStore(AbstractDocumentStore):
    """Production MongoDB backend built on motor.

    Features:

    - Connection pooling (motor handles internally)
    - Multi-document ACID transactions via sessions
    - Configurable read/write concerns
    - Health check with server ping
    - BSON codec configuration for custom types

    Usage::

        store = MongoDBDocumentStore(config)
        await store.connect()
        users = store.collection("users")
        await users.insert_one({"name": "Alice"})
        await store.disconnect()
    """

    def __init__(self, config: MongoDBConfig) -> None:
        super().__init__(database_name=config.database)
        self._config = config
        self._client: Any = None
        self._db: Any = None

    async def connect(self) -> None:
        """Connect to MongoDB using motor async client."""
        try:
            import motor.motor_asyncio as motor
        except ImportError as exc:
            raise NoSQLConnectionError(
                "motor is required for MongoDB support. "
                "Install with: pip install lexigram-nosql[mongodb]"
            ) from exc

        codec_options = configure_codecs()
        client_kwargs: dict[str, Any] = {
            "maxPoolSize": self._config.max_pool_size,
            "minPoolSize": self._config.min_pool_size,
            "serverSelectionTimeoutMS": self._config.server_selection_timeout_ms,
            "connectTimeoutMS": self._config.connect_timeout_ms,
            "socketTimeoutMS": self._config.socket_timeout_ms,
            "retryWrites": self._config.retry_writes,
            "retryReads": self._config.retry_reads,
        }
        self._client = motor.AsyncIOMotorClient(
            self._config.uri,
            **client_kwargs,
        )
        self._db = self._client[self._database_name]
        if codec_options is not None:
            self._db = self._db.with_options(codec_options=codec_options)

        # Verify connectivity
        try:
            await self._client.admin.command("ping")
        except Exception as exc:
            self._client.close()
            self._client = None
            self._db = None
            raise NoSQLConnectionError(
                f"Failed to connect to MongoDB at {self._config.uri}: {exc}"
            ) from exc

        self._connected = True
        logger.info(
            "nosql.mongodb.connected",
            database=self._database_name,
            pool_max=self._config.max_pool_size,
        )

    async def disconnect(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._collections.clear()
            self._connected = False
            logger.info(
                "nosql.mongodb.disconnected",
                database=self._database_name,
            )

    def _create_collection(self, name: str) -> MongoDBCollection:  # type: ignore[override]
        """Create a MongoDBCollection wrapper."""
        if self._db is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        return MongoDBCollection(self._db[name])

    def session(self) -> AbstractAsyncContextManager[Any]:
        """Create a MongoDB client session for transactions."""
        if self._client is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        return mongodb_session(self._client)

    async def list_collections(self) -> list[str]:
        """List all collection names in the database."""
        if self._db is None:
            raise RuntimeError("Not connected to MongoDB.")
        collections: list[str] = await self._db.list_collection_names()
        return collections

    async def drop_collection(self, name: str) -> None:
        """Drop a collection by name."""
        if self._db is None:
            raise RuntimeError("Not connected to MongoDB.")
        await self._db.drop_collection(name)
        self._collections.pop(name, None)
        logger.info("nosql.mongodb.collection_dropped", collection=name)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check MongoDB connectivity with a ping command."""
        if not self._client or not self._connected:
            return HealthCheckResult(
                component="mongodb",
                status=HealthStatus.UNHEALTHY,
                message="Not connected",
            )
        try:
            await asyncio.wait_for(
                self._client.admin.command("ping"),
                timeout=timeout,
            )
            return HealthCheckResult(
                component="mongodb",
                status=HealthStatus.HEALTHY,
                message=f"Connected to {self._database_name}",
            )
        except TimeoutError:
            return HealthCheckResult(
                component="mongodb",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {timeout}s",
            )
        except pymongo.errors.PyMongoError as exc:
            return HealthCheckResult(
                component="mongodb",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {exc}",
            )

    def get_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics."""
        if not self._client:
            return {}
        return {
            "max_pool_size": self._config.max_pool_size,
            "min_pool_size": self._config.min_pool_size,
            "connected": self._connected,
        }

    def get_query_stats(self) -> dict[str, Any]:
        """Get query execution statistics.

        Note: Exact query stats require motor APM command listeners.
        This provides a structural basis compatible with infrastructure monitoring.
        """
        return {}


__all__ = ["MongoDBDocumentStore"]
