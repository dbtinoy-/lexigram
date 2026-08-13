"""Unit tests for vector configuration classes."""

from __future__ import annotations

import pytest

from lexigram.contracts.core.config import Environment
from lexigram.contracts.data.vector.enums import DistanceMetric, IndexType
from lexigram.vector.config import (
    ChromaConfig,
    MemoryConfig,
    NamedVectorConfig,
    PgVectorConfig,
    PineconeConfig,
    QdrantConfig,
    VectorConfig,
    WeaviateConfig,
)
from lexigram.vector import constants as const


class TestPgVectorConfig:
    def test_default_values(self) -> None:
        config = PgVectorConfig()
        assert config.database == "primary"
        assert config.schema == "public"
        assert config.default_lists == const.PGVECTOR_DEFAULT_LISTS
        assert config.default_probes == const.PGVECTOR_DEFAULT_PROBES
        assert config.default_ef_search == const.PGVECTOR_DEFAULT_EF_SEARCH
        assert config.table_prefix == "vec_"
        assert config.create_extension is True

    def test_custom_values(self) -> None:
        config = PgVectorConfig(
            database="custom",
            schema="custom_schema",
            default_lists=200,
            default_probes=10,
            default_ef_search=64,
            table_prefix="custom_",
            create_extension=False,
        )
        assert config.database == "custom"
        assert config.schema == "custom_schema"
        assert config.default_lists == 200
        assert config.default_probes == 10
        assert config.default_ef_search == 64
        assert config.table_prefix == "custom_"
        assert config.create_extension is False

    def test_empty_database_validation(self) -> None:
        with pytest.raises(ValueError, match="must be a non-empty"):
            PgVectorConfig(database="   ")


class TestChromaConfig:
    def test_default_values(self) -> None:
        config = ChromaConfig()
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.use_http_client is True
        assert config.api_key is None
        assert config.collection_name == "default"
        assert config.timeout == 30.0

    def test_custom_values(self) -> None:
        config = ChromaConfig(
            host="0.0.0.0",
            port=9000,
            use_http_client=False,
            api_key="secret",
            collection_name="test",
            timeout=60.0,
        )
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.use_http_client is False
        assert config.api_key.get_secret_value() == "secret"
        assert config.collection_name == "test"
        assert config.timeout == 60.0


class TestPineconeConfig:
    def test_default_values(self) -> None:
        config = PineconeConfig()
        assert config.api_key.get_secret_value() == ""
        assert config.environment == ""
        assert config.index_name == ""
        assert config.namespace == ""
        assert config.timeout == const.DEFAULT_REQUEST_TIMEOUT
        assert config.pool_threads == 4

    def test_custom_values(self) -> None:
        config = PineconeConfig(
            api_key="sk-test",
            environment="us-west1-gcp",
            index_name="my-index",
            namespace="test-ns",
            timeout=120.0,
            pool_threads=8,
        )
        assert config.api_key.get_secret_value() == "sk-test"
        assert config.environment == "us-west1-gcp"
        assert config.index_name == "my-index"
        assert config.namespace == "test-ns"
        assert config.timeout == 120.0
        assert config.pool_threads == 8


class TestQdrantConfig:
    def test_default_values(self) -> None:
        config = QdrantConfig()
        assert config.url == "http://localhost:6333"
        assert config.api_key is None
        assert config.grpc_port == 6334
        assert config.prefer_grpc is True
        assert config.timeout == const.DEFAULT_REQUEST_TIMEOUT

    def test_custom_values(self) -> None:
        config = QdrantConfig(
            url="http://qdrant:6333",
            api_key="secret",
            grpc_port=6335,
            prefer_grpc=False,
            timeout=60.0,
        )
        assert config.url == "http://qdrant:6333"
        assert config.api_key.get_secret_value() == "secret"
        assert config.grpc_port == 6335
        assert config.prefer_grpc is False
        assert config.timeout == 60.0


class TestWeaviateConfig:
    def test_default_values(self) -> None:
        config = WeaviateConfig()
        assert config.url == "http://localhost:8080"
        assert config.api_key is None
        assert config.grpc_port == 50051
        assert config.timeout == const.DEFAULT_REQUEST_TIMEOUT

    def test_custom_values(self) -> None:
        config = WeaviateConfig(
            url="http://weaviate:8080",
            api_key="secret",
            grpc_port=50052,
            timeout=120.0,
        )
        assert config.url == "http://weaviate:8080"
        assert config.api_key.get_secret_value() == "secret"
        assert config.grpc_port == 50052
        assert config.timeout == 120.0


class TestMemoryConfig:
    def test_default_values(self) -> None:
        config = MemoryConfig()
        assert config.max_collections == 100
        assert config.max_vectors_per_collection == 100_000

    def test_custom_values(self) -> None:
        config = MemoryConfig(
            max_collections=50,
            max_vectors_per_collection=10_000,
        )
        assert config.max_collections == 50
        assert config.max_vectors_per_collection == 10_000


class TestVectorConfig:
    def test_default_values(self) -> None:
        config = VectorConfig()
        assert config.enabled is True
        assert config.backend == const.BACKEND_MEMORY
        assert config.default_distance_metric == DistanceMetric.COSINE
        assert config.default_index_type == IndexType.HNSW
        assert config.default_dimension == 1536
        assert config.upsert_batch_size == const.DEFAULT_UPSERT_BATCH_SIZE
        assert config.max_retries == const.DEFAULT_MAX_RETRIES
        assert config.retry_delay == const.DEFAULT_RETRY_DELAY
        assert config.backends == []
        assert config.collection_name == "default"
        assert config.enable_cache is False
        assert config.cache_ttl == 86400
        assert config.embedding_model == "text-embedding-3-small"

    def test_custom_backend(self) -> None:
        config = VectorConfig(backend=const.BACKEND_QDRANT)
        assert config.backend == const.BACKEND_QDRANT

    def test_invalid_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported backend"):
            VectorConfig(backend="invalid")

    def test_backend_validation(self) -> None:
        config = VectorConfig(backend=const.BACKEND_PINECONE)
        assert config.backend == const.BACKEND_PINECONE

        config = VectorConfig(backend=const.BACKEND_PGVECTOR)
        assert config.backend == const.BACKEND_PGVECTOR

        config = VectorConfig(backend=const.BACKEND_CHROMA)
        assert config.backend == const.BACKEND_CHROMA

        config = VectorConfig(backend=const.BACKEND_WEAVIATE)
        assert config.backend == const.BACKEND_WEAVIATE


class TestVectorConfigEnvironmentValidation:
    def test_production_memory_backend_error(self) -> None:
        config = VectorConfig(backend=const.BACKEND_MEMORY)
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "memory" in issues[0].message.lower() or "in-memory" in issues[0].message.lower()

    def test_production_chroma_backend_error(self) -> None:
        config = VectorConfig(backend=const.BACKEND_CHROMA)
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert len(issues) == 1
        assert issues[0].severity == "error"

    def test_production_qdrant_backend_ok(self) -> None:
        config = VectorConfig(backend=const.BACKEND_QDRANT)
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert issues == []

    def test_production_pgvector_backend_ok(self) -> None:
        config = VectorConfig(backend=const.BACKEND_PGVECTOR)
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert issues == []

    def test_production_pinecone_missing_api_key(self) -> None:
        config = VectorConfig(
            backend=const.BACKEND_PINECONE,
            pinecone=PineconeConfig(api_key=""),
        )
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert len(issues) == 1
        assert issues[0].severity == "error"

    def test_development_no_pinecone_api_key_error(self) -> None:
        config = VectorConfig(
            backend=const.BACKEND_PINECONE,
            pinecone=PineconeConfig(api_key=""),
        )
        issues = config.validate_for_environment(Environment.DEVELOPMENT)
        assert issues == []


class TestVectorConfigFromNamed:
    def test_from_named_creates_single_backend_config(self) -> None:
        named = NamedVectorConfig(
            name="custom",
            primary=True,
            backend=const.BACKEND_QDRANT,
            qdrant=QdrantConfig(url="http://custom:6333"),
        )
        base = VectorConfig(
            default_dimension=768,
            default_distance_metric=DistanceMetric.EUCLIDEAN,
            upsert_batch_size=100,
        )
        config = VectorConfig.from_named(named, base)

        assert config.backend == const.BACKEND_QDRANT
        assert config.qdrant.url == "http://custom:6333"
        assert config.default_dimension == 768
        assert config.default_distance_metric == DistanceMetric.EUCLIDEAN
        assert config.upsert_batch_size == 100
        assert config.backends == []

    def test_from_named_with_empty_base(self) -> None:
        named = NamedVectorConfig(
            name="memory",
            backend=const.BACKEND_MEMORY,
        )
        config = VectorConfig.from_named(named)

        assert config.backend == const.BACKEND_MEMORY
        assert config.backends == []


class TestNamedVectorConfig:
    def test_default_values(self) -> None:
        config = NamedVectorConfig(name="test")
        assert config.name == "test"
        assert config.primary is False
        assert config.backend == const.BACKEND_MEMORY

    def test_primary_backend_qdrant(self) -> None:
        config = NamedVectorConfig(
            name="primary",
            primary=True,
            backend=const.BACKEND_QDRANT,
            qdrant=QdrantConfig(url="http://qdrant:6333"),
        )
        assert config.name == "primary"
        assert config.primary is True
        assert config.backend == const.BACKEND_QDRANT
        assert config.qdrant.url == "http://qdrant:6333"

    def test_invalid_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported vector backend"):
            NamedVectorConfig(name="test", backend="invalid")

    def test_all_supported_backends(self) -> None:
        for backend in (
            const.BACKEND_MEMORY,
            const.BACKEND_PGVECTOR,
            const.BACKEND_PINECONE,
            const.BACKEND_QDRANT,
            const.BACKEND_CHROMA,
            const.BACKEND_WEAVIATE,
        ):
            config = NamedVectorConfig(name="test", backend=backend)
            assert config.backend == backend