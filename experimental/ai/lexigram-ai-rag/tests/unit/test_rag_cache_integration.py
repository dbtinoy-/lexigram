from __future__ import annotations

from _test_rag_cache_support import MockCacheBackend
import pytest

from lexigram.ai.rag.cache import RAGCache


class TestCacheIntegration:
    """Integration tests for RAG cache."""

    @pytest.mark.asyncio
    async def test_full_rag_pipeline_caching(self) -> None:
        """Test caching in a complete RAG pipeline scenario."""
        cache = RAGCache(backend=MockCacheBackend())

        # Step 1: Cache query transformation
        original_query = "what is ai?"
        transformed_query = "What is artificial intelligence?"
        await cache.cache_query_transformation(
            original_query,
            "rewrite",
            transformed_query,
        )

        # Step 2: Cache embedding for transformed query
        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        await cache.cache_embedding(transformed_query, "ada-002", query_embedding)

        # Step 3: Cache retrieval results
        retrieval_results = [
            {"content": "AI is...", "score": 0.95, "id": "doc1"},
            {"content": "Artificial intelligence...", "score": 0.87, "id": "doc2"},
        ]
        await cache.cache_retrieval(transformed_query, retrieval_results)

        # Step 4: Cache reranking scores
        doc_ids = ["doc1", "doc2"]
        reranking_scores = [0.92, 0.88]
        await cache.cache_reranking(
            transformed_query,
            doc_ids,
            "cross-encoder",
            reranking_scores,
        )

        # Verify all cached data can be retrieved
        assert (
            await cache.get_query_transformation(original_query, "rewrite")
            == transformed_query
        )
        assert (
            await cache.get_embedding(transformed_query, "ada-002") == query_embedding
        )
        assert await cache.get_retrieval(transformed_query) == retrieval_results
        assert (
            await cache.get_reranking(transformed_query, doc_ids, "cross-encoder")
            == reranking_scores
        )

        # Check statistics
        stats = await cache.get_stats()
        assert stats["hits"] == 4  # 4 successful retrievals
        assert stats["sets"] == 4  # 4 cache operations
        assert stats["hit_rate"] == 1.0  # 100% hit rate

    @pytest.mark.asyncio
    async def test_cache_invalidation_workflow(self) -> None:
        """Test cache invalidation in workflow."""
        cache = RAGCache(backend=MockCacheBackend())

        # Cache data for multiple documents
        for i in range(5):
            await cache.cache_document(
                f"doc_{i}",
                {"content": f"Document {i}"},
                {"extract_tables": True},
            )

        # Verify all cached
        stats = await cache.get_stats()
        assert stats["total_entries"] == 5

        # Invalidate all document caches
        invalidated = await cache.invalidate_pattern("document:")
        assert invalidated == 5

        # Verify all were invalidated
        stats = await cache.get_stats()
        assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_mixed_cache_types(self) -> None:
        """Test using different cache types together."""
        cache = RAGCache(backend=MockCacheBackend())

        # Cache different types
        await cache.cache_embedding("text", "model", [0.1, 0.2])
        await cache.cache_retrieval("query", [{"doc": "1"}])
        await cache.cache_document("doc_id", {"content": "text"})
        await cache.cache_reranking("query", ["doc1"], "model", [0.9])
        await cache.cache_query_transformation("q", "rewrite", "Q")

        # Verify all types are cached
        stats = await cache.get_stats()
        assert stats["total_entries"] == 5
        assert stats["sets"] == 5

        # Invalidate only embeddings
        count = await cache.invalidate_pattern("embedding:")
        assert count == 1

        # Others should remain
        stats = await cache.get_stats()
        assert stats["total_entries"] == 4
