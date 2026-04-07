"""In-memory vector store implementation for testing and local development."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import uuid

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.data.vector import (
    CollectionInfo,
    DeleteResult,
    DistanceMetric,
    IndexState,
    IndexType,
    SearchResult,
    UpsertResult,
    VectorRecord,
)
from lexigram.contracts.data.vector.filters import (
    FilterOperator,
    LogicalOperator,
    MetadataCondition,
    MetadataConditionGroup,
    MetadataFilter,
)
from lexigram.vector.backends.base import BaseVectorCollection, BaseVectorStore
from lexigram.vector.config import MemoryConfig
from lexigram.vector.exceptions import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    DimensionMismatchError,
)

if TYPE_CHECKING:
    from lexigram.contracts.data.vector import CollectionConfig, SearchQuery


class MemoryVectorStore(BaseVectorStore):
    """Non-persistent in-memory vector store."""

    def __init__(self, config: MemoryConfig | None = None):
        self._config = config or MemoryConfig()
        self._collections: dict[str, MemoryVectorCollection] = {}
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if not self._connected:
            return HealthCheckResult(
                component="memory_vector_store",
                status=HealthStatus.UNHEALTHY,
                message="Memory store disconnected",
            )
        return HealthCheckResult(
            component="memory_vector_store",
            status=HealthStatus.HEALTHY,
        )

    async def list_collections(self) -> list[CollectionInfo]:
        return [
            CollectionInfo(
                name=collection.name,
                dimension=collection.dimension,
                distance_metric=collection.distance_metric,
                index_type=IndexType.FLAT,
                vector_count=await collection.count(),
                state=IndexState.READY,
            )
            for collection in self._collections.values()
        ]

    async def create_collection(self, config: CollectionConfig) -> None:
        if config.name in self._collections:
            raise CollectionAlreadyExistsError(config.name)

        self._collections[config.name] = MemoryVectorCollection(
            name=config.name,
            dimension=config.dimension,
            distance_metric=config.distance_metric,
        )

    async def delete_collection(self, name: str) -> None:
        if name not in self._collections:
            raise CollectionNotFoundError(name)
        del self._collections[name]

    async def collection_exists(self, name: str) -> bool:
        return name in self._collections

    async def get_collection(self, name: str) -> MemoryVectorCollection:
        if name not in self._collections:
            raise CollectionNotFoundError(name)
        return self._collections[name]

    async def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
        collection_name: str | None = None,
    ) -> UpsertResult:
        name = collection_name or "default"
        if not await self.collection_exists(name):
            raise CollectionNotFoundError(name)
        if embeddings is None:
            raise ValueError("embeddings must be provided")
        col = await self.get_collection(name)
        return await col.add_texts(texts, embeddings, metadatas)


class MemoryVectorCollection(BaseVectorCollection):
    """In-memory vector collection implementation."""

    def __init__(
        self,
        name: str,
        dimension: int,
        distance_metric: DistanceMetric,
    ):
        super().__init__(name, dimension, distance_metric)
        self._records: dict[str, VectorRecord] = {}

    async def upsert(self, records: list[VectorRecord]) -> UpsertResult:
        for record in records:
            if len(record.vector) != self.dimension:
                raise DimensionMismatchError(
                    expected=self.dimension,
                    actual=len(record.vector),
                    record_id=record.id,
                )
            self._records[record.id] = record
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
        if len(query.vector) != self.dimension:
            raise DimensionMismatchError(
                expected=self.dimension,
                actual=len(query.vector),
            )

        results: list[SearchResult] = []
        for record in self._records.values():
            if query.filter and not self._matches_filter(record.metadata, query.filter):
                continue

            score = self._calculate_similarity(query.vector, record.vector)
            if query.min_score is not None and score < query.min_score:
                continue

            results.append(
                SearchResult(
                    id=record.id,
                    score=score,
                    metadata=dict(record.metadata) if query.include_metadata else {},
                    vector=record.vector if query.include_vectors else None,
                    content=record.content,
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        return results[: query.top_k]

    async def get(self, ids: list[str]) -> list[VectorRecord]:
        return [
            self._records[record_id] for record_id in ids if record_id in self._records
        ]

    async def delete(self, ids: list[str]) -> DeleteResult:
        count = 0
        for record_id in ids:
            if record_id in self._records:
                del self._records[record_id]
                count += 1
        return DeleteResult(deleted_count=count)

    async def delete_by_filter(self, filter: MetadataFilter) -> DeleteResult:
        to_delete = [
            record_id
            for record_id, record in self._records.items()
            if self._matches_filter(record.metadata, filter)
        ]
        for record_id in to_delete:
            del self._records[record_id]
        return DeleteResult(deleted_count=len(to_delete))

    async def count(self) -> int:
        return len(self._records)

    async def update_metadata(self, record_id: str, metadata: dict[str, Any]) -> bool:
        if record_id not in self._records:
            return False

        old_record = self._records[record_id]
        new_metadata = {**old_record.metadata, **metadata}
        self._records[record_id] = VectorRecord(
            id=old_record.id,
            vector=old_record.vector,
            metadata=new_metadata,
            content=old_record.content,
        )
        return True

    def _calculate_similarity(self, v1: list[float], v2: list[float]) -> float:
        if self.distance_metric == DistanceMetric.COSINE:
            return self._cosine_similarity(v1, v2)
        if self.distance_metric == DistanceMetric.EUCLIDEAN:
            dist = sum((a - b) ** 2 for a, b in zip(v1, v2, strict=False)) ** 0.5
            return float(1.0 / (1.0 + dist))
        if self.distance_metric == DistanceMetric.DOT_PRODUCT:
            return float(sum(a * b for a, b in zip(v1, v2, strict=False)))
        return 0.0

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        dot_product = sum(a * b for a, b in zip(v1, v2, strict=False))
        norm_v1 = sum(a * a for a in v1) ** 0.5
        norm_v2 = sum(a * a for a in v2) ** 0.5
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return float(dot_product / (norm_v1 * norm_v2))

    def _matches_filter(
        self,
        metadata: dict[str, Any],
        filter_obj: MetadataFilter,
    ) -> bool:
        if isinstance(filter_obj, MetadataCondition):
            return self._evaluate_condition(metadata, filter_obj)

        if isinstance(filter_obj, MetadataConditionGroup):
            evaluations = [
                self._matches_filter(metadata, cond) for cond in filter_obj.conditions
            ]
            if filter_obj.logical_operator == LogicalOperator.AND:
                return all(evaluations)
            return any(evaluations)

        return True

    def _evaluate_condition(
        self,
        metadata: dict[str, Any],
        condition: MetadataCondition,
    ) -> bool:
        key = condition.field
        operator = condition.operator
        expected = condition.value

        exists = key in metadata
        actual = metadata.get(key)

        if operator == FilterOperator.EXISTS:
            return exists is bool(expected)
        if not exists:
            return False

        if operator == FilterOperator.EQ:
            return bool(actual == expected)
        if operator == FilterOperator.NE:
            return bool(actual != expected)
        if operator == FilterOperator.GT:
            return bool(actual > expected)
        if operator == FilterOperator.GTE:
            return bool(actual >= expected)
        if operator == FilterOperator.LT:
            return bool(actual < expected)
        if operator == FilterOperator.LTE:
            return bool(actual <= expected)
        if operator == FilterOperator.IN:
            return actual in expected
        if operator == FilterOperator.NOT_IN:
            return actual not in expected
        if operator == FilterOperator.CONTAINS:
            return str(expected) in str(actual)

        return False


InMemoryVectorStore = MemoryVectorStore
InMemoryVectorCollection = MemoryVectorCollection

__all__ = [
    "InMemoryVectorCollection",
    "InMemoryVectorStore",
    "MemoryVectorCollection",
    "MemoryVectorStore",
]
