"""Qdrant vector database driver."""

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
from lexigram.logging import get_logger
from lexigram.vector.backends.base import BaseVectorStore
from lexigram.vector.backends.qdrant.collection import QdrantCollection

if TYPE_CHECKING:
    from qdrant_client import AsyncQdrantClient

    from lexigram.vector.config import QdrantConfig

logger = get_logger(__name__)


class QdrantStore(BaseVectorStore):
    """Qdrant vector database driver."""

    def __init__(self, config: QdrantConfig):
        self._config = config
        self._client: AsyncQdrantClient | None = None

    async def connect(self) -> None:
        from qdrant_client import AsyncQdrantClient

        self._client = AsyncQdrantClient(
            url=self._config.url,
            api_key=self._config.api_key.get_secret_value()
            if self._config.api_key
            else None,
            port=self._config.grpc_port if self._config.prefer_grpc else None,
            prefer_grpc=self._config.prefer_grpc,
        )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if not self._client:
            return HealthCheckResult(component="qdrant", status=HealthStatus.UNHEALTHY)
        try:
            return HealthCheckResult(component="qdrant", status=HealthStatus.HEALTHY)
        except Exception as exc:  # noqa: BLE001  # health check must catch all Qdrant client failures
            return HealthCheckResult(
                component="qdrant",
                status=HealthStatus.UNHEALTHY,
                message=str(exc),
            )

    async def list_collections(self) -> list[CollectionInfo]:
        if not self._client:
            raise RuntimeError("Not connected")

        collections_res = await self._client.get_collections()
        results = []
        for collection in collections_res.collections:
            info = await self._client.get_collection(collection.name)
            results.append(
                CollectionInfo(
                    name=collection.name,
                    dimension=info.config.params.vectors.size,
                    distance_metric=self._map_distance(
                        info.config.params.vectors.distance
                    ),
                    index_type=IndexType.HNSW,
                    vector_count=info.vectors_count,
                    state=IndexState.READY
                    if info.status == "green"
                    else IndexState.UPDATING,
                )
            )
        return results

    async def create_collection(self, config: CollectionConfig) -> None:
        if not self._client:
            raise RuntimeError("Not connected")
        from qdrant_client.http import models

        await self._client.create_collection(
            collection_name=config.name,
            vectors_config=models.VectorParams(
                size=config.dimension,
                distance=self._unmap_distance(config.distance_metric),
            ),
        )
        try:
            await self._client.create_payload_index(
                collection_name=config.name,
                field_name="content",
                field_schema=models.TextIndexParams(
                    type="text",
                    tokenizer=models.TokenizerType.WORD,
                    min_token_len=2,
                    max_token_len=15,
                    lowercase=True,
                ),
            )
        except Exception as e:  # noqa: BLE001 — collection setup is best-effort; text index creation may not be supported
            logger.debug(
                "qdrant_text_index_setup_failed", collection=config.name, error=str(e)
            )

    async def delete_collection(self, name: str) -> None:
        if not self._client:
            raise RuntimeError("Not connected")
        await self._client.delete_collection(name)

    async def collection_exists(self, name: str) -> bool:
        if not self._client:
            raise RuntimeError("Not connected")
        return bool(await self._client.collection_exists(name))

    async def get_collection(self, name: str) -> QdrantCollection:
        if not self._client:
            raise RuntimeError("Not connected")
        info = await self._client.get_collection(name)
        return QdrantCollection(
            self._client,
            name,
            info.config.params.vectors.size,
            self._map_distance(info.config.params.vectors.distance),
        )

    def _map_distance(self, distance: str) -> DistanceMetric:
        mapping = {
            "Cosine": DistanceMetric.COSINE,
            "Euclid": DistanceMetric.EUCLIDEAN,
            "Dot": DistanceMetric.DOT_PRODUCT,
            "Manhattan": DistanceMetric.MANHATTAN,
        }
        return mapping.get(distance, DistanceMetric.COSINE)

    def _unmap_distance(self, distance: DistanceMetric) -> Any:
        from qdrant_client.http import models

        mapping = {
            DistanceMetric.COSINE: models.Distance.COSINE,
            DistanceMetric.EUCLIDEAN: models.Distance.EUCLID,
            DistanceMetric.DOT_PRODUCT: models.Distance.DOT,
            DistanceMetric.MANHATTAN: models.Distance.MANHATTAN,
        }
        return mapping.get(distance, models.Distance.COSINE)

    async def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
        collection_name: str | None = None,
    ) -> UpsertResult:
        name = collection_name or "default"
        if not await self.collection_exists(name):
            raise RuntimeError(f"Collection {name} does not exist")
        if embeddings is None:
            raise ValueError("embeddings must be provided")
        col = await self.get_collection(name)
        return await col.add_texts(texts, embeddings, metadatas)
