"""pgvector collection implementation."""

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
from lexigram.serialization.backends.json import loads
from lexigram.vector.backends.base import BaseVectorCollection

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol
    from lexigram.contracts.data.vector.filters import MetadataFilter


class PgVectorCollection(BaseVectorCollection):
    """PostgreSQL vector collection implementation."""

    def __init__(
        self,
        provider: DatabaseProviderProtocol,
        name: str,
        dimension: int,
        distance_metric: DistanceMetric,
    ):
        super().__init__(name, dimension, distance_metric)
        self._provider = provider

    async def upsert(self, records: list[VectorRecord]) -> UpsertResult:
        if not records:
            return UpsertResult(upserted_count=0)

        sql = (
            f'INSERT INTO "{self.name}" (id, embedding, metadata, content) '
            "VALUES ($1, $2::vector, $3::jsonb, $4) "
            "ON CONFLICT (id) DO UPDATE SET "
            "embedding = EXCLUDED.embedding, "
            "metadata = EXCLUDED.metadata, "
            "content = EXCLUDED.content"
        )

        args = [
            (record.id, str(record.vector), record.metadata, record.content)
            for record in records
        ]

        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            await conn.executemany(sql, args)  # type: ignore[attr-defined]

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
        import re

        from lexigram.vector.backends.pgvector.filters import PgVectorFilterCompiler

        op = self._get_distance_operator()
        vec_str = str(query.vector)

        score_expr = f"1 - (embedding {op} $1::vector)"
        if self.distance_metric == DistanceMetric.DOT_PRODUCT:
            score_expr = f"-(embedding {op} $1::vector)"

        sql = f'SELECT id, metadata, content, {score_expr} as score FROM "{self.name}"'
        params: list[Any] = [vec_str]

        if query.filter:
            compiler = PgVectorFilterCompiler()
            filter_sql, filter_params = compiler.compile(query.filter)
            filter_sql_shifted = re.sub(
                r"\$(\d+)", lambda m: f"${int(m.group(1)) + 1}", filter_sql
            )
            sql = (
                f"SELECT id, metadata, content, {score_expr} as score "
                f'FROM "{self.name}" WHERE {filter_sql_shifted}'
            )
            params.extend(filter_params)

        sql += f" ORDER BY embedding {op} $1::vector LIMIT {query.top_k}"
        result = await self._provider.execute_query(sql, params)

        search_results: list[SearchResult] = []
        for row in result:
            metadata = row["metadata"] if query.include_metadata else {}
            search_results.append(
                SearchResult(
                    id=row["id"],
                    score=float(row["score"]),
                    metadata=metadata,
                    content=row["content"],
                )
            )

        return search_results

    async def get(self, ids: list[str]) -> list[VectorRecord]:
        sql = f'SELECT id, embedding, metadata, content FROM "{self.name}" WHERE id = ANY($1)'
        result = await self._provider.execute_query(sql, [ids])

        records: list[VectorRecord] = []
        for row in result:
            embedding = row["embedding"]
            vector = embedding if isinstance(embedding, list) else loads(embedding)
            records.append(
                VectorRecord(
                    id=row["id"],
                    vector=vector,
                    metadata=row["metadata"],
                    content=row["content"],
                )
            )
        return records

    async def delete(self, ids: list[str]) -> DeleteResult:
        result = await self._provider.execute_delete(self.name, "id = ANY($1)", [ids])
        return DeleteResult(deleted_count=result.affected_rows)

    async def delete_by_filter(self, filter: MetadataFilter) -> DeleteResult:
        from lexigram.vector.backends.pgvector.filters import PgVectorFilterCompiler

        compiler = PgVectorFilterCompiler()
        filter_sql, filter_params = compiler.compile(filter)

        result = await self._provider.execute_delete(
            self.name, filter_sql, filter_params
        )
        return DeleteResult(deleted_count=result.affected_rows)

    async def count(self) -> int:
        sql = f'SELECT count(*) as count FROM "{self.name}"'
        result = await self._provider.execute_query(sql)
        return int(result[0]["count"])

    async def update_metadata(self, record_id: str, metadata: dict[str, Any]) -> bool:
        result = await self._provider.execute_update(
            self.name,
            {"metadata": metadata},
            "id = $1",
            [record_id],
        )
        return result.affected_rows > 0

    def _get_distance_operator(self) -> str:
        if self.distance_metric == DistanceMetric.COSINE:
            return "<=>"
        if self.distance_metric == DistanceMetric.EUCLIDEAN:
            return "<->"
        if self.distance_metric == DistanceMetric.DOT_PRODUCT:
            return "<#>"
        return "<=>"
