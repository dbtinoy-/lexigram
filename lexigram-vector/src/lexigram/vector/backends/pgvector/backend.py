"""PostgreSQL pgvector implementation using the framework's DatabaseProviderProtocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.data.vector import (
    CollectionConfig,
    CollectionInfo,
    DistanceMetric,
    IndexState,
    IndexType,
    UpsertResult,
)
from lexigram.vector.backends.base import BaseVectorStore
from lexigram.vector.backends.pgvector.collection import PgVectorCollection
from lexigram.vector.config import PgVectorConfig

if TYPE_CHECKING:
    from lexigram.contracts.core.health import HealthCheckResult
    from lexigram.contracts.data import DatabaseProviderProtocol


class PgVectorStore(BaseVectorStore):
    """PostgreSQL vector store using pgvector extension."""

    def __init__(
        self, provider: DatabaseProviderProtocol, config: PgVectorConfig | None = None
    ):
        self._provider = provider
        self._config = config or PgVectorConfig()

    async def connect(self) -> None:
        await self._provider.connect()
        # Ensure pgvector extension exists
        await self._provider.execute("CREATE EXTENSION IF NOT EXISTS vector")

    async def disconnect(self) -> None:
        await self._provider.disconnect()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        return await self._provider.health_check(timeout=timeout)

    async def list_collections(self) -> list[CollectionInfo]:
        sql = """
            SELECT table_name, column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE udt_name = 'vector'
        """
        result = await self._provider.execute_query(sql)

        collections = []
        for row in result:
            table_name = row["table_name"]
            collections.append(
                CollectionInfo(
                    name=table_name,
                    dimension=0,
                    distance_metric=DistanceMetric.COSINE,
                    index_type=IndexType.HNSW,
                    vector_count=0,
                    state=IndexState.READY,
                )
            )
        return collections

    async def create_collection(self, config: CollectionConfig) -> None:
        table_name = config.name
        dim = config.dimension

        sql = f"""
            CREATE TABLE IF NOT EXISTS "{table_name}" (
                id TEXT PRIMARY KEY,
                embedding vector({dim}),
                metadata JSONB,
                content TEXT
            )
        """
        await self._provider.execute(sql)

        index_name = f"idx_{table_name}_embedding"
        ops = self._get_operator_class(config.distance_metric)
        index_type = "hnsw" if config.index_type == IndexType.HNSW else "ivfflat"

        if index_type == "hnsw":
            # HNSW with configurable m and ef_construction
            m = config.hnsw_m or 16
            ef_construction = config.hnsw_ef_construction or 64
            index_sql = f"""
                CREATE INDEX IF NOT EXISTS "{index_name}" ON "{table_name}" 
                USING hnsw (embedding {ops})
                WITH (m = {m}, ef_construction = {ef_construction})
            """
        else:
            # IVFFlat with default lists
            index_sql = f"""
                CREATE INDEX IF NOT EXISTS "{index_name}" ON "{table_name}" 
                USING ivfflat (embedding {ops}) WITH (lists = 100)
            """

        await self._provider.execute(index_sql)

        # Add metadata GIN index for faster JSONB filtering
        await self._provider.execute(
            f'CREATE INDEX IF NOT EXISTS "idx_{table_name}_metadata" ON "{table_name}" USING gin (metadata)'
        )

    async def delete_collection(self, name: str) -> None:
        await self._provider.execute(f'DROP TABLE IF EXISTS "{name}"')

    async def collection_exists(self, name: str) -> bool:
        return await self._provider.table_exists(name)

    async def get_collection(self, name: str) -> PgVectorCollection:
        return PgVectorCollection(self._provider, name, 0, DistanceMetric.COSINE)

    def _get_operator_class(self, metric: DistanceMetric) -> str:
        if metric == DistanceMetric.COSINE:
            return "vector_cosine_ops"
        if metric == DistanceMetric.EUCLIDEAN:
            return "vector_l2_ops"
        if metric == DistanceMetric.DOT_PRODUCT:
            return "vector_ip_ops"
        return "vector_cosine_ops"

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
