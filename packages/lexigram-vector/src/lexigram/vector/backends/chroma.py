"""ChromaDB vector store backend for lexigram-vector.

Supports both in-process (EphemeralClient) and HTTP (HttpClient) modes.
All ChromaDB operations are synchronous and are wrapped with
``asyncio.to_thread`` to keep the async interface non-blocking.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any
import uuid

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.data.vector import (
    CollectionConfig,
    CollectionInfo,
    DeleteResult,
    DistanceMetric,
    IndexState,
    IndexType,
    SearchQuery,
    SearchResult,
    UpsertResult,
    VectorRecord,
)
from lexigram.logging import get_logger
from lexigram.vector.backends.base import BaseVectorCollection, BaseVectorStore
from lexigram.vector.backends.chroma_filters import ChromaFilterCompiler
from lexigram.vector.exceptions import VectorConnectionError

if TYPE_CHECKING:
    import chromadb

    from lexigram.vector.config import ChromaConfig

logger = get_logger(__name__)

_CHROMA_DISTANCE_MAP: dict[DistanceMetric, str] = {
    DistanceMetric.COSINE: "cosine",
    DistanceMetric.EUCLIDEAN: "l2",
    DistanceMetric.DOT_PRODUCT: "ip",
}

_REVERSE_DISTANCE_MAP: dict[str, DistanceMetric] = {
    v: k for k, v in _CHROMA_DISTANCE_MAP.items()
}


class ChromaCollection(BaseVectorCollection):
    """ChromaDB vector collection implementation."""

    def __init__(
        self,
        collection: Any,  # chromadb.Collection
        name: str,
        dimension: int,
        distance_metric: DistanceMetric,
    ) -> None:
        super().__init__(name, dimension, distance_metric)
        self._collection = collection

    async def update_metadata(self, record_id: str, metadata: dict[str, Any]) -> bool:
        """Update metadata for a single vector record.

        ChromaDB supports metadata-only updates via its update API.
        Fetches the existing record, merges metadata, then updates.

        Args:
            record_id: ID of the record to update.
            metadata: Key-value pairs to merge into existing metadata.

        Returns:
            True if the record existed and was updated, False otherwise.
        """
        try:
            existing = await asyncio.to_thread(
                self._collection.get, ids=[record_id], include=["metadatas"]
            )
            if not existing["ids"]:
                return False
            merged = {**(existing["metadatas"][0] or {}), **metadata}
            await asyncio.to_thread(
                self._collection.update,
                ids=[record_id],
                metadatas=[merged],
            )
            return True
        except Exception:  # noqa: BLE001
            logger.warning("chroma_update_metadata_failed", record_id=record_id)
            return False

    async def upsert(self, records: list[VectorRecord]) -> UpsertResult:
        """Upsert vector records into the collection."""
        if not records:
            return UpsertResult(upserted_count=0)

        ids = [r.id for r in records]
        embeddings = [r.vector for r in records]
        metadatas = [dict(r.metadata) for r in records]
        documents = [r.content or "" for r in records]

        await asyncio.to_thread(
            self._collection.upsert,
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        return UpsertResult(upserted_count=len(records))

    async def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> UpsertResult:
        records = [
            VectorRecord(
                id=ids[i] if ids else str(uuid.uuid4()),
                vector=embeddings[i],
                metadata=metadatas[i] if metadatas else {},
                content=text,
            )
            for i, text in enumerate(texts)
        ]
        return await self.upsert(records)

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        """Search the collection by vector similarity."""
        where: dict[str, Any] | None = None
        if query.filter is not None:
            where = ChromaFilterCompiler().compile(query.filter)

        kwargs: dict[str, Any] = {
            "query_embeddings": [query.vector],
            "n_results": query.top_k,
            "include": ["metadatas", "documents", "distances", "embeddings"]
            if query.include_vectors
            else ["metadatas", "documents", "distances"],
        }
        if where is not None:
            kwargs["where"] = where

        results = await asyncio.to_thread(self._collection.query, **kwargs)

        search_results: list[SearchResult] = []
        if not results["ids"] or not results["ids"][0]:
            return search_results

        ids = results["ids"][0]
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]
        documents = results["documents"][0]
        embeddings = results.get("embeddings", [[None] * len(ids)])[0]

        for i, record_id in enumerate(ids):
            # Chroma returns distances (lower = more similar); convert to score
            score = 1.0 - distances[i] if distances[i] is not None else 0.0
            if query.min_score is not None and score < query.min_score:
                continue
            search_results.append(
                SearchResult(
                    id=record_id,
                    score=score,
                    metadata=dict(metadatas[i] or {}),
                    content=documents[i] or None,
                    vector=embeddings[i] if query.include_vectors else None,
                )
            )
        return search_results

    async def get(self, ids: list[str]) -> list[VectorRecord]:
        """Retrieve records by ID."""
        results = await asyncio.to_thread(
            self._collection.get,
            ids=ids,
            include=["metadatas", "documents", "embeddings"],
        )
        records: list[VectorRecord] = []
        for i, record_id in enumerate(results["ids"]):
            records.append(
                VectorRecord(
                    id=record_id,
                    vector=results["embeddings"][i] if results["embeddings"] else [],
                    metadata=dict(results["metadatas"][i] or {}),
                    content=results["documents"][i] or None,
                )
            )
        return records

    async def delete(self, ids: list[str]) -> DeleteResult:
        """Delete records by ID."""
        await asyncio.to_thread(self._collection.delete, ids=ids)
        return DeleteResult(deleted_count=len(ids))

    async def delete_by_filter(self, filter: Any) -> DeleteResult:
        """Delete records matching a MetadataFilter or raw Chroma ``where`` clause."""
        from lexigram.contracts.data.vector.filters import (
            MetadataCondition,
            MetadataConditionGroup,
        )

        where = (
            ChromaFilterCompiler().compile(filter)
            if isinstance(filter, (MetadataCondition, MetadataConditionGroup))
            else filter
        )
        await asyncio.to_thread(self._collection.delete, where=where)
        return DeleteResult(deleted_count=-1)

    async def count(self) -> int:
        """Return number of vectors in the collection."""
        return await asyncio.to_thread(self._collection.count)


class ChromaStore(BaseVectorStore):
    """ChromaDB vector store backend.

    Supports two operating modes:

    - **In-process** (``use_http_client=False``): Uses ``EphemeralClient``
      for fast in-memory storage. Ideal for testing and local development.
    - **HTTP** (``use_http_client=True``): Connects to a running ChromaDB
      server via ``HttpClient``.

    Usage::

        store = ChromaStore(config)
        await store.connect()
        col = await store.get_collection("my-collection")
        await col.upsert([VectorRecord(id="1", vector=[0.1, 0.2], metadata={})])
        results = await col.search(SearchQuery(vector=[0.1, 0.2], top_k=5))
        await store.disconnect()
    """

    def __init__(self, config: ChromaConfig) -> None:
        self._config = config
        self._client: chromadb.ClientAPI | None = None

    async def connect(self) -> None:
        """Initialize the ChromaDB client."""
        import chromadb

        def _create_client() -> chromadb.ClientAPI:
            if self._config.use_http_client:
                settings = chromadb.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
                kwargs: dict[str, Any] = {
                    "host": self._config.host,
                    "port": self._config.port,
                    "settings": settings,
                }
                if self._config.api_key:
                    kwargs["headers"] = {
                        "X-Chroma-Token": self._config.api_key.get_secret_value()
                    }
                return chromadb.HttpClient(**kwargs)
            return chromadb.EphemeralClient()

        try:
            self._client = await asyncio.to_thread(_create_client)
            logger.info(
                "chroma_connected", host=self._config.host, port=self._config.port
            )
        except Exception as exc:
            raise VectorConnectionError(
                f"Failed to connect to ChromaDB: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """Release the ChromaDB client."""
        self._client = None
        logger.info("chroma_disconnected")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check ChromaDB connectivity."""
        if not self._client:
            return HealthCheckResult(
                component="chroma",
                status=HealthStatus.UNHEALTHY,
                message="Not connected",
            )
        start = time.monotonic()
        try:
            version = await asyncio.to_thread(self._client.get_version)
            duration_ms = (time.monotonic() - start) * 1000
            return HealthCheckResult(
                component="chroma",
                status=HealthStatus.HEALTHY,
                message=f"ChromaDB {version}",
                duration_ms=duration_ms,
                details={"version": version},
            )
        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.monotonic() - start) * 1000
            return HealthCheckResult(
                component="chroma",
                status=HealthStatus.UNHEALTHY,
                message=str(exc),
                duration_ms=duration_ms,
            )

    async def list_collections(self) -> list[CollectionInfo]:
        """List all ChromaDB collections."""
        if not self._client:
            raise RuntimeError("Not connected")
        collections = await asyncio.to_thread(self._client.list_collections)
        return [
            CollectionInfo(
                name=col.name,
                dimension=0,  # Chroma doesn't expose dimension in metadata
                distance_metric=_REVERSE_DISTANCE_MAP.get(
                    (col.metadata or {}).get("hnsw:space", "cosine"),
                    DistanceMetric.COSINE,
                ),
                index_type=IndexType.HNSW,
                vector_count=0,
                state=IndexState.READY,
            )
            for col in collections
        ]

    async def create_collection(self, config: CollectionConfig) -> None:
        """Create a new ChromaDB collection."""
        if not self._client:
            raise RuntimeError("Not connected")
        distance = _CHROMA_DISTANCE_MAP.get(config.distance_metric, "cosine")
        await asyncio.to_thread(
            self._client.create_collection,
            name=config.name,
            metadata={"hnsw:space": distance},
            get_or_create=False,
        )

    async def delete_collection(self, name: str) -> None:
        """Delete a ChromaDB collection."""
        if not self._client:
            raise RuntimeError("Not connected")
        await asyncio.to_thread(self._client.delete_collection, name)

    async def collection_exists(self, name: str) -> bool:
        """Check if a collection exists."""
        if not self._client:
            raise RuntimeError("Not connected")
        try:
            await asyncio.to_thread(self._client.get_collection, name)
            return True
        except Exception:  # noqa: BLE001
            return False

    async def get_collection(self, name: str) -> ChromaCollection:
        """Get a handle to an existing collection."""
        if not self._client:
            raise RuntimeError("Not connected")
        col = await asyncio.to_thread(self._client.get_collection, name)
        metadata = col.metadata or {}
        distance_str = metadata.get("hnsw:space", "cosine")
        distance_metric = _REVERSE_DISTANCE_MAP.get(distance_str, DistanceMetric.COSINE)
        return ChromaCollection(
            collection=col,
            name=name,
            dimension=0,
            distance_metric=distance_metric,
        )

    async def get_or_create_collection(
        self, config: CollectionConfig
    ) -> ChromaCollection:
        """Get or create a collection."""
        if not self._client:
            raise RuntimeError("Not connected")
        distance = _CHROMA_DISTANCE_MAP.get(config.distance_metric, "cosine")
        col = await asyncio.to_thread(
            self._client.get_or_create_collection,
            name=config.name,
            metadata={"hnsw:space": distance},
        )
        return ChromaCollection(
            collection=col,
            name=config.name,
            dimension=config.dimension,
            distance_metric=config.distance_metric,
        )


__all__ = ["ChromaCollection", "ChromaStore"]
