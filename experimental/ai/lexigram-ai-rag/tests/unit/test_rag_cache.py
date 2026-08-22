from __future__ import annotations

from lexigram.ai.rag.cache import (
    CacheKeyBuilder,
    RAGCacheConfig,
    RAGCacheStats,
)


class TestCacheKeyBuilder:
    """Tests for CacheKeyBuilderProtocol."""

    def test_embedding_key_consistency(self):
        """Test that same inputs produce same key."""
        key1 = CacheKeyBuilder.build_embedding_key("hello", "ada-002")
        key2 = CacheKeyBuilder.build_embedding_key("hello", "ada-002")
        assert key1 == key2

    def test_embedding_key_uniqueness(self):
        """Test that different inputs produce different keys."""
        key1 = CacheKeyBuilder.build_embedding_key("hello", "ada-002")
        key2 = CacheKeyBuilder.build_embedding_key("world", "ada-002")
        key3 = CacheKeyBuilder.build_embedding_key("hello", "text-embedding-3-small")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_embedding_key_format(self):
        """Test embedding key format."""
        key = CacheKeyBuilder.build_embedding_key("text", "model", "test:")
        assert key.startswith("test:embedding:")
        assert len(key.split(":")) == 3

    def test_retrieval_key_consistency(self):
        """Test retrieval key consistency."""
        params = {"top_k": 5, "threshold": 0.7}
        key1 = CacheKeyBuilder.build_retrieval_key("query", params)
        key2 = CacheKeyBuilder.build_retrieval_key("query", params)
        assert key1 == key2

    def test_retrieval_key_param_order_independence(self):
        """Test that param order doesn't affect key."""
        params1 = {"top_k": 5, "threshold": 0.7}
        params2 = {"threshold": 0.7, "top_k": 5}  # Different order

        key1 = CacheKeyBuilder.build_retrieval_key("query", params1)
        key2 = CacheKeyBuilder.build_retrieval_key("query", params2)
        assert key1 == key2

    def test_retrieval_key_different_params(self):
        """Test that different params produce different keys."""
        key1 = CacheKeyBuilder.build_retrieval_key("query", {"top_k": 5})
        key2 = CacheKeyBuilder.build_retrieval_key("query", {"top_k": 10})
        assert key1 != key2

    def test_document_key_consistency(self):
        """Test document key consistency."""
        config = {"extract_tables": True, "ocr": False}
        key1 = CacheKeyBuilder.build_document_key("doc_123", config)
        key2 = CacheKeyBuilder.build_document_key("doc_123", config)
        assert key1 == key2

    def test_document_key_different_config(self):
        """Test different configs produce different keys."""
        key1 = CacheKeyBuilder.build_document_key("doc_123", {"ocr": True})
        key2 = CacheKeyBuilder.build_document_key("doc_123", {"ocr": False})
        assert key1 != key2

    def test_reranking_key_consistency(self):
        """Test reranking key consistency."""
        doc_ids = ["doc1", "doc2", "doc3"]
        key1 = CacheKeyBuilder.build_reranking_key("query", doc_ids, "model")
        key2 = CacheKeyBuilder.build_reranking_key("query", doc_ids, "model")
        assert key1 == key2

    def test_reranking_key_doc_order_independence(self):
        """Test that document ID order doesn't affect key (they're sorted)."""
        key1 = CacheKeyBuilder.build_reranking_key(
            "query",
            ["doc1", "doc2", "doc3"],
            "model",
        )
        key2 = CacheKeyBuilder.build_reranking_key(
            "query",
            ["doc3", "doc1", "doc2"],
            "model",
        )
        assert key1 == key2  # Should be same due to sorting

    def test_query_transformation_key_consistency(self):
        """Test query transformation key consistency."""
        params = {"model": "gpt-4"}
        key1 = CacheKeyBuilder.build_query_transformation_key(
            "query",
            "rewrite",
            params,
        )
        key2 = CacheKeyBuilder.build_query_transformation_key(
            "query",
            "rewrite",
            params,
        )
        assert key1 == key2

    def test_query_transformation_key_different_types(self):
        """Test different transformation types produce different keys."""
        key1 = CacheKeyBuilder.build_query_transformation_key("query", "rewrite")
        key2 = CacheKeyBuilder.build_query_transformation_key("query", "expansion")
        assert key1 != key2


class TestCacheStats:
    """Tests for RAGCacheStats."""

    def test_cache_stats_defaults(self):
        """Test RAGCacheStats default values."""
        stats = RAGCacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.errors == 0

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = RAGCacheStats(hits=75, misses=25)
        assert stats.hit_rate == 0.75

    def test_hit_rate_zero_operations(self):
        """Test hit rate with zero operations."""
        stats = RAGCacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_all_hits(self):
        """Test hit rate with all hits."""
        stats = RAGCacheStats(hits=100, misses=0)
        assert stats.hit_rate == 1.0

    def test_hit_rate_all_misses(self):
        """Test hit rate with all misses."""
        stats = RAGCacheStats(hits=0, misses=100)
        assert stats.hit_rate == 0.0

    def test_total_operations(self):
        """Test total operations calculation."""
        stats = RAGCacheStats(hits=50, misses=30, sets=20, deletes=10)
        assert stats.total_operations == 110  # hits + misses + sets + deletes


class TestRAGCacheConfig:
    """Tests for RAGCacheConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RAGCacheConfig()

        assert config.embedding_ttl == 86400  # 24 hours
        assert config.retrieval_ttl == 300  # 5 minutes
        assert config.document_ttl == 3600  # 1 hour
        assert config.reranking_ttl == 600  # 10 minutes
        assert config.llm_response_ttl == 1800  # 30 minutes
        assert config.query_transformation_ttl == 3600  # 1 hour
        assert config.key_prefix == "rag:"
        assert config.enable_stats is True
        assert config.max_embedding_cache_size == 10000
        assert config.max_retrieval_cache_size == 1000

    def test_custom_config(self):
        """Test custom configuration."""
        config = RAGCacheConfig(
            embedding_ttl=7200,
            retrieval_ttl=600,
            key_prefix="myapp:",
            enable_stats=False,
        )

        assert config.embedding_ttl == 7200
        assert config.retrieval_ttl == 600
        assert config.key_prefix == "myapp:"
        assert config.enable_stats is False
