"""Pinecone vector collection implementation."""

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
    try:
        from pinecone import Index
    except ImportError:
        Index = Any


class PineconeCollection(BaseVectorCollection):
    """Pinecone vector collection implementation."""

    def __init__(
        self,
        index: Index,
        name: str,
        dimension: int,
        distance_metric: DistanceMetric,
    ):
        super().__init__(name, dimension, distance_metric)
        self._index = index

    async def upsert(self, records: list[VectorRecord]) -> UpsertResult:
        to_upsert: list[dict[str, Any]] = []
        for record in records:
            metadata = dict(record.metadata)
            if record.content is not None:
                metadata["content"] = record.content
            to_upsert.append(
                {
                    "id": record.id,
                    "values": record.vector,
                    "metadata": metadata,
                }
            )

        res = await self._index.upsert(vectors=to_upsert)
        return UpsertResult(upserted_count=res.upserted_count)

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
        filter_dict = None
        if query.filter:
            from lexigram.vector.backends.pinecone.filters import PineconeFilterCompiler

            compiler = PineconeFilterCompiler()
            filter_dict = compiler.compile(query.filter)

        res = await self._index.query(
            vector=query.vector,
            top_k=query.top_k,
            include_metadata=query.include_metadata,
            include_values=query.include_vectors,
            filter=filter_dict,
        )

        results: list[SearchResult] = []
        for match in res.matches:
            metadata = dict(match.metadata or {})
            content = metadata.pop("content", None)
            results.append(
                SearchResult(
                    id=match.id,
                    score=match.score,
                    metadata=metadata,
                    vector=match.values if query.include_vectors else None,
                    content=content,
                )
            )
        return results

    async def get(self, ids: list[str]) -> list[VectorRecord]:
        res = await self._index.fetch(ids=ids)
        records: list[VectorRecord] = []
        for record_id, match in res.vectors.items():
            metadata = dict(match.metadata or {})
            content = metadata.pop("content", None)
            records.append(
                VectorRecord(
                    id=record_id,
                    vector=match.values,
                    metadata=metadata,
                    content=content,
                )
            )
        return records

    async def delete(self, ids: list[str]) -> DeleteResult:
        await self._index.delete(ids=ids)
        return DeleteResult(deleted_count=len(ids))

    async def delete_by_filter(self, filter: Any) -> DeleteResult:
        await self._index.delete(filter=filter)
        return DeleteResult(deleted_count=0)

    async def count(self) -> int:
        stats = await self._index.describe_index_stats()
        return int(getattr(stats, "total_vector_count", 0))

    async def update_metadata(self, record_id: str, metadata: dict[str, Any]) -> bool:
        await self._index.update(id=record_id, set_metadata=metadata)
        return True
