"""Tests for NamedVectorConfig and VectorConfig.backends / from_named()."""

from __future__ import annotations

import pytest

from lexigram.contracts.data.vector.enums import DistanceMetric, IndexType
from lexigram.contracts.exceptions import ValidationError
from lexigram.vector.config import (
    MemoryConfig,
    NamedVectorConfig,
    PgVectorConfig,
    PineconeConfig,
    QdrantConfig,
    VectorConfig,
)


class TestNamedVectorConfig:
    """Unit tests for NamedVectorConfig."""

    def test_requires_name(self) -> None:
        """NamedVectorConfig.name is a mandatory field."""
        with pytest.raises(ValidationError):
            NamedVectorConfig()  # type: ignore[call-arg]

    def test_primary_defaults_to_false(self) -> None:
        """NamedVectorConfig.primary defaults to False."""
        cfg = NamedVectorConfig(name="rag")
        assert cfg.primary is False

    def test_backend_defaults_to_memory(self) -> None:
        """NamedVectorConfig.backend defaults to 'memory'."""
        cfg = NamedVectorConfig(name="rag")
        assert cfg.backend == "memory"

    def test_primary_flag_is_settable(self) -> None:
        """primary=True marks the backend as the default unnamed binding."""
        cfg = NamedVectorConfig(name="main", primary=True)
        assert cfg.primary is True

    def test_sub_configs_have_defaults(self) -> None:
        """All per-driver sub-configs are created with their defaults."""
        cfg = NamedVectorConfig(name="semantic")
        assert isinstance(cfg.pgvector, PgVectorConfig)
        assert isinstance(cfg.pinecone, PineconeConfig)
        assert isinstance(cfg.qdrant, QdrantConfig)
        assert isinstance(cfg.memory, MemoryConfig)

    def test_custom_qdrant_config_is_preserved(self) -> None:
        """A custom QdrantConfig passed to NamedVectorConfig is retained."""
        qdrant = QdrantConfig(url="http://qdrant.internal:6333", prefer_grpc=False)
        cfg = NamedVectorConfig(name="semantic", backend="qdrant", qdrant=qdrant)
        assert cfg.qdrant.url == "http://qdrant.internal:6333"
        assert cfg.qdrant.prefer_grpc is False

    def test_custom_pgvector_config_is_preserved(self) -> None:
        """A custom PgVectorConfig passed to NamedVectorConfig is retained."""
        pgvec = PgVectorConfig(database="rag", schema="vectors")
        cfg = NamedVectorConfig(name="rag", backend="pgvector", pgvector=pgvec)
        assert cfg.pgvector.database == "rag"
        assert cfg.pgvector.schema == "vectors"

    def test_custom_pinecone_config_is_preserved(self) -> None:
        """A custom PineconeConfig passed to NamedVectorConfig is retained."""

        pinecone = PineconeConfig(index_name="my-index", namespace="prod")
        cfg = NamedVectorConfig(name="pine", backend="pinecone", pinecone=pinecone)
        assert cfg.pinecone.index_name == "my-index"
        assert cfg.pinecone.namespace == "prod"

    def test_custom_memory_config_is_preserved(self) -> None:
        """A custom MemoryConfig passed to NamedVectorConfig is retained."""
        memory = MemoryConfig(max_collections=5, max_vectors_per_collection=1000)
        cfg = NamedVectorConfig(name="test", memory=memory)
        assert cfg.memory.max_collections == 5
        assert cfg.memory.max_vectors_per_collection == 1000


class TestVectorConfigBackends:
    """Unit tests for VectorConfig.backends and from_named()."""

    def test_backends_defaults_to_empty_list(self) -> None:
        """VectorConfig.backends is an empty list by default."""
        cfg = VectorConfig()
        assert cfg.backends == []

    def test_backward_compat_without_backends(self) -> None:
        """VectorConfig without backends works exactly as before."""
        cfg = VectorConfig(backend="qdrant")
        assert cfg.backend == "qdrant"
        assert cfg.backends == []

    def test_backends_accepts_named_entries(self) -> None:
        """VectorConfig.backends stores all declared named entries."""
        primary = NamedVectorConfig(name="primary", primary=True, backend="qdrant")
        rag = NamedVectorConfig(name="rag", backend="pgvector")
        cfg = VectorConfig(backends=[primary, rag])
        assert len(cfg.backends) == 2
        assert cfg.backends[0].name == "primary"
        assert cfg.backends[1].name == "rag"

    def test_non_primary_entry_is_usable(self) -> None:
        """A non-primary named entry can be read without primary=True."""
        entry = NamedVectorConfig(name="semantic", backend="memory")
        cfg = VectorConfig(backends=[entry])
        assert cfg.backends[0].primary is False
        assert cfg.backends[0].name == "semantic"

    def test_primary_entry_is_detectable(self) -> None:
        """An entry with primary=True is detectable via the flag."""
        primary_entry = NamedVectorConfig(name="main", primary=True, backend="qdrant")
        cfg = VectorConfig(backends=[primary_entry])
        assert any(b.primary for b in cfg.backends)

    def test_from_named_sets_backend(self) -> None:
        """from_named() sets backend from the entry."""
        entry = NamedVectorConfig(name="vec", backend="qdrant")
        result = VectorConfig.from_named(entry)
        assert result.backend == "qdrant"

    def test_from_named_sets_backends_empty(self) -> None:
        """from_named() always sets backends=[] to prevent recursion."""
        entry = NamedVectorConfig(name="vec", backend="memory")
        cfg = VectorConfig(backends=[entry])
        result = VectorConfig.from_named(entry, base=cfg)
        assert result.backends == []

    def test_from_named_preserves_pgvector_config(self) -> None:
        """from_named() carries through the entry's PgVectorConfig."""
        pgvec = PgVectorConfig(database="rag", schema="vectors")
        entry = NamedVectorConfig(name="rag", backend="pgvector", pgvector=pgvec)
        result = VectorConfig.from_named(entry)
        assert result.pgvector.database == "rag"
        assert result.pgvector.schema == "vectors"

    def test_from_named_preserves_qdrant_config(self) -> None:
        """from_named() carries through the entry's QdrantConfig."""
        qdrant = QdrantConfig(url="http://qdrant.internal:6333")
        entry = NamedVectorConfig(name="sem", backend="qdrant", qdrant=qdrant)
        result = VectorConfig.from_named(entry)
        assert result.qdrant.url == "http://qdrant.internal:6333"

    def test_from_named_preserves_pinecone_config(self) -> None:
        """from_named() carries through the entry's PineconeConfig."""
        pinecone = PineconeConfig(index_name="prod-index", namespace="app")
        entry = NamedVectorConfig(name="pine", backend="pinecone", pinecone=pinecone)
        result = VectorConfig.from_named(entry)
        assert result.pinecone.index_name == "prod-index"
        assert result.pinecone.namespace == "app"

    def test_from_named_copies_default_dimension_from_base(self) -> None:
        """from_named() inherits default_dimension from the base config."""
        base = VectorConfig(default_dimension=768)
        entry = NamedVectorConfig(name="small", backend="memory")
        result = VectorConfig.from_named(entry, base=base)
        assert result.default_dimension == 768

    def test_from_named_copies_global_settings_from_base(self) -> None:
        """from_named() copies all global settings from the base config."""
        base = VectorConfig(
            default_distance_metric=DistanceMetric.DOT_PRODUCT,
            default_index_type=IndexType.FLAT,
            default_dimension=512,
            upsert_batch_size=50,
            max_retries=5,
            retry_delay=1.0,
        )
        entry = NamedVectorConfig(name="custom", backend="memory")
        result = VectorConfig.from_named(entry, base=base)
        assert result.default_distance_metric == DistanceMetric.DOT_PRODUCT
        assert result.default_index_type == IndexType.FLAT
        assert result.default_dimension == 512
        assert result.upsert_batch_size == 50
        assert result.max_retries == 5
        assert result.retry_delay == 1.0

    def test_from_named_without_base_uses_defaults(self) -> None:
        """from_named() without a base falls back to VectorConfig defaults."""
        entry = NamedVectorConfig(name="default-test", backend="memory")
        result = VectorConfig.from_named(entry)
        assert result.default_dimension == 1536  # VectorConfig default
        assert result.backends == []
