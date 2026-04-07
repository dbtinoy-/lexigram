"""Pinecone managed vector store driver."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.data.vector import (
    CollectionConfig,
    CollectionInfo,
    DistanceMetric,
    IndexState,
    IndexType,
    UpsertResult,
)
from lexigram.vector.backends.base import BaseVectorStore
from lexigram.vector.backends.pinecone.collection import PineconeCollection

if TYPE_CHECKING:
    from lexigram.vector.config import PineconeConfig

    try:
        from pinecone import PineconeAsyncio as Pinecone
    except ImportError:
        Pinecone = Any


class PineconeStore(BaseVectorStore):
    """Pinecone managed vector store driver (SDK v6+)."""

    def __init__(self, config: PineconeConfig):
        self._config = config
        self._api_key = config.api_key.get_secret_value()
        self._environment = config.environment
        self._client: Pinecone | None = None

    async def connect(self) -> None:
        from pinecone import PineconeAsyncio

        self._client = PineconeAsyncio(api_key=self._api_key)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if not self._client:
            return HealthCheckResult(
                component="pinecone", status=HealthStatus.UNHEALTHY
            )
        try:
            await self._client.list_indexes()
            return HealthCheckResult(component="pinecone", status=HealthStatus.HEALTHY)
        except Exception as exc:  # noqa: BLE001  # health check must catch all Pinecone client failures
            return HealthCheckResult(
                component="pinecone",
                status=HealthStatus.UNHEALTHY,
                message=str(exc),
            )

    async def list_collections(self) -> list[CollectionInfo]:
        if not self._client:
            raise RuntimeError("Not connected")

        indexes = await self._client.list_indexes()
        collections = []
        for idx in indexes:
            desc = await self._client.describe_index(idx.name)
            collections.append(
                CollectionInfo(
                    name=idx.name,
                    dimension=desc.dimension,
                    distance_metric=self._map_metric(desc.metric),
                    index_type=IndexType.HNSW,
                    vector_count=0,
                    state=IndexState.READY
                    if desc.status.ready
                    else IndexState.CREATING,
                )
            )
        return collections

    async def create_collection(self, config: CollectionConfig) -> None:
        if not self._client:
            raise RuntimeError("Not connected")
        from pinecone import ServerlessSpec

        spec = ServerlessSpec(cloud="aws", region="us-east-1")
        await self._client.create_index(
            name=config.name,
            dimension=config.dimension,
            metric=self._unmap_metric(config.distance_metric),
            spec=spec,
        )

    async def delete_collection(self, name: str) -> None:
        if not self._client:
            raise RuntimeError("Not connected")
        await self._client.delete_index(name)

    async def collection_exists(self, name: str) -> bool:
        if not self._client:
            raise RuntimeError("Not connected")
        indexes = await self._client.list_indexes()
        return any(idx.name == name for idx in indexes)

    async def get_collection(self, name: str) -> PineconeCollection:
        if not self._client:
            raise RuntimeError("Not connected")
        desc = await self._client.describe_index(name)
        index = self._client.IndexAsyncio(host=desc.host)
        return PineconeCollection(
            index,
            name,
            desc.dimension,
            self._map_metric(desc.metric),
        )

    def _map_metric(self, metric: str) -> DistanceMetric:
        mapping = {
            "cosine": DistanceMetric.COSINE,
            "euclidean": DistanceMetric.EUCLIDEAN,
            "dotproduct": DistanceMetric.DOT_PRODUCT,
        }
        return mapping.get(metric, DistanceMetric.COSINE)

    def _unmap_metric(self, metric: DistanceMetric) -> str:
        mapping = {
            DistanceMetric.COSINE: "cosine",
            DistanceMetric.EUCLIDEAN: "euclidean",
            DistanceMetric.DOT_PRODUCT: "dotproduct",
        }
        return mapping.get(metric, "cosine")

    async def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
        collection_name: str | None = None,
    ) -> UpsertResult:
        name = collection_name or self._config.index_name
        if not await self.collection_exists(name):
            raise RuntimeError(f"Collection {name} does not exist")
        if embeddings is None:
            raise ValueError("embeddings must be provided")
        col = await self.get_collection(name)
        return await col.add_texts(texts, embeddings, metadatas)
