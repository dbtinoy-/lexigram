"""Qdrant vector collection implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import uuid

from lexigram.contracts.data.vector import (
    DeleteResult,
    DistanceMetric,
    SearchQuery,
    SearchResult,
    UpsertResult,
    VectorRecord,
)
from lexigram.vector.backends.base import BaseVectorCollection

if TYPE_CHECKING:
    from qdrant_client import AsyncQdrantClient


class QdrantCollection(BaseVectorCollection):
    """Qdrant vector collection implementation."""

    def __init__(
        self,
        client: AsyncQdrantClient,
        name: str,
        dimension: int,
        distance_metric: DistanceMetric,
    ):
        super().__init__(name, dimension, distance_metric)
        self._client = client

    async def upsert(self, records: list[VectorRecord]) -> UpsertResult:
        from qdrant_client.http import models

        points = []
        for record in records:
            payload = dict(record.metadata)
            if record.content:
                payload["content"] = record.content
            points.append(
                models.PointStruct(
                    id=record.id,
                    vector=record.vector,
                    payload=payload,
                )
            )

        await self._client.upsert(collection_name=self.name, points=points)
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
        qdrant_filter = None
        if query.filter:
            from lexigram.vector.backends.qdrant.filters import QdrantFilterCompiler

            compiler = QdrantFilterCompiler()
            qdrant_filter = compiler.compile(query.filter)

        res = await self._client.search(
            collection_name=self.name,
            query_vector=query.vector,
            limit=query.top_k,
            with_payload=query.include_metadata,
            with_vectors=query.include_vectors,
            score_threshold=query.min_score,
            query_filter=qdrant_filter,
        )

        results: list[SearchResult] = []
        for scored_point in res:
            payload = dict(scored_point.payload or {})
            content = payload.pop("content", None)
            results.append(
                SearchResult(
                    id=str(scored_point.id),
                    score=float(scored_point.score),
                    metadata=payload,
                    vector=scored_point.vector if query.include_vectors else None,
                    content=content,
                )
            )
        return results

    async def get(self, ids: list[str]) -> list[VectorRecord]:
        res = await self._client.retrieve(
            collection_name=self.name,
            ids=ids,
            with_payload=True,
            with_vectors=True,
        )
        records: list[VectorRecord] = []
        for point in res:
            payload = dict(point.payload or {})
            content = payload.pop("content", None)
            vector = point.vector if isinstance(point.vector, list) else []
            records.append(
                VectorRecord(
                    id=str(point.id),
                    vector=vector,
                    metadata=payload,
                    content=content,
                )
            )
        return records

    async def delete(self, ids: list[str]) -> DeleteResult:
        from qdrant_client.http import models

        await self._client.delete(
            collection_name=self.name,
            points_selector=models.PointIdsList(points=ids),
        )
        return DeleteResult(deleted_count=len(ids))

    async def delete_by_filter(self, filter: Any) -> DeleteResult:
        from lexigram.vector.backends.qdrant.filters import QdrantFilterCompiler

        compiler = QdrantFilterCompiler()
        qdrant_filter = compiler.compile(filter)
        await self._client.delete(
            collection_name=self.name,
            points_selector=qdrant_filter,
        )
        return DeleteResult(deleted_count=0)

    async def count(self) -> int:
        info = await self._client.get_collection(self.name)
        return int(info.vectors_count or 0)

    async def update_metadata(self, record_id: str, metadata: dict[str, Any]) -> bool:
        await self._client.set_payload(
            collection_name=self.name,
            payload=metadata,
            points=[record_id],
        )
        return True
