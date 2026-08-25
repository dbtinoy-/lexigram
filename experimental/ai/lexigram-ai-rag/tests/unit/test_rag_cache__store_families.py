from __future__ import annotations

import pytest

from lexigram.ai.rag.cache import RAGCache


class TestRAGCache:
    """Tests for RAGCache store families (embedding, retrieval, document,
    reranking, and query transformation)."""

    # Embedding cache tests

    @pytest.mark.asyncio
    async def test_cache_and_get_embedding(self, cache: RAGCache) -> None:
        """Test caching and retrieving embeddings."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        await cache.cache_embedding("hello world", "ada-002", embedding)
        cached = await cache.get_embedding("hello world", "ada-002")

        assert cached == embedding

    @pytest.mark.asyncio
    async def test_get_nonexistent_embedding(self, cache: RAGCache) -> None:
        """Test getting non-existent embedding returns None."""
        result = await cache.get_embedding("nonexistent", "ada-002")
        assert result is None

    @pytest.mark.asyncio
    async def test_embedding_cache_different_models(self, cache: RAGCache) -> None:
        """Test embeddings are cached separately per model."""
        embedding1 = [0.1, 0.2, 0.3]
        embedding2 = [0.4, 0.5, 0.6]

        await cache.cache_embedding("text", "ada-002", embedding1)
        await cache.cache_embedding("text", "text-embedding-3-small", embedding2)

        cached1 = await cache.get_embedding("text", "ada-002")
        cached2 = await cache.get_embedding("text", "text-embedding-3-small")

        assert cached1 == embedding1
        assert cached2 == embedding2
        assert cached1 != cached2

    @pytest.mark.asyncio
    async def test_embedding_cache_different_texts(self, cache: RAGCache) -> None:
        """Test embeddings are cached separately per text."""
        embedding1 = [0.1, 0.2, 0.3]
        embedding2 = [0.4, 0.5, 0.6]

        await cache.cache_embedding("hello", "ada-002", embedding1)
        await cache.cache_embedding("world", "ada-002", embedding2)

        cached1 = await cache.get_embedding("hello", "ada-002")
        cached2 = await cache.get_embedding("world", "ada-002")

        assert cached1 == embedding1
        assert cached2 == embedding2

    # Retrieval cache tests

    @pytest.mark.asyncio
    async def test_cache_and_get_retrieval(self, cache: RAGCache) -> None:
        """Test caching and retrieving retrieval results."""
        results = [
            {"content": "Doc 1", "score": 0.95},
            {"content": "Doc 2", "score": 0.87},
        ]
        params = {"top_k": 5, "threshold": 0.7}

        await cache.cache_retrieval("What is AI?", results, params)
        cached = await cache.get_retrieval("What is AI?", params)

        assert cached == results

    @pytest.mark.asyncio
    async def test_get_nonexistent_retrieval(self, cache: RAGCache) -> None:
        """Test getting non-existent retrieval returns None."""
        result = await cache.get_retrieval("nonexistent query", {"top_k": 5})
        assert result is None

    @pytest.mark.asyncio
    async def test_retrieval_cache_different_params(self, cache: RAGCache) -> None:
        """Test retrieval results cached separately per params."""
        results1 = [{"content": "Doc 1", "score": 0.95}]
        results2 = [
            {"content": "Doc 1", "score": 0.95},
            {"content": "Doc 2", "score": 0.87},
        ]

        await cache.cache_retrieval("query", results1, {"top_k": 1})
        await cache.cache_retrieval("query", results2, {"top_k": 2})

        cached1 = await cache.get_retrieval("query", {"top_k": 1})
        cached2 = await cache.get_retrieval("query", {"top_k": 2})

        assert len(cached1) == 1
        assert len(cached2) == 2

    @pytest.mark.asyncio
    async def test_retrieval_cache_no_params(self, cache: RAGCache) -> None:
        """Test retrieval caching without params."""
        results = [{"content": "Doc 1"}]

        await cache.cache_retrieval("query", results)
        cached = await cache.get_retrieval("query")

        assert cached == results

    # Document cache tests

    @pytest.mark.asyncio
    async def test_cache_and_get_document(self, cache: RAGCache) -> None:
        """Test caching and retrieving documents."""
        document = {
            "content": "Processed text",
            "metadata": {"title": "Doc 1", "author": "Jane"},
        }
        config = {"extract_tables": True, "ocr": False}

        await cache.cache_document("doc_123", document, config)
        cached = await cache.get_document("doc_123", config)

        assert cached == document

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self, cache: RAGCache) -> None:
        """Test getting non-existent document returns None."""
        result = await cache.get_document("nonexistent_doc", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_document_cache_different_configs(self, cache: RAGCache) -> None:
        """Test documents cached separately per config."""
        doc1 = {"content": "With OCR"}
        doc2 = {"content": "Without OCR"}

        await cache.cache_document("doc_123", doc1, {"ocr": True})
        await cache.cache_document("doc_123", doc2, {"ocr": False})

        cached1 = await cache.get_document("doc_123", {"ocr": True})
        cached2 = await cache.get_document("doc_123", {"ocr": False})

        assert cached1 == doc1
        assert cached2 == doc2

    # Reranking cache tests

    @pytest.mark.asyncio
    async def test_cache_and_get_reranking(self, cache: RAGCache) -> None:
        """Test caching and retrieving reranking scores."""
        doc_ids = ["doc1", "doc2", "doc3"]
        scores = [0.95, 0.87, 0.72]

        await cache.cache_reranking("query", doc_ids, "cross-encoder", scores)
        cached = await cache.get_reranking("query", doc_ids, "cross-encoder")

        assert cached == scores

    @pytest.mark.asyncio
    async def test_get_nonexistent_reranking(self, cache: RAGCache) -> None:
        """Test getting non-existent reranking returns None."""
        result = await cache.get_reranking("query", ["doc1"], "model")
        assert result is None

    @pytest.mark.asyncio
    async def test_reranking_cache_different_models(self, cache: RAGCache) -> None:
        """Test reranking cached separately per model."""
        doc_ids = ["doc1", "doc2"]
        scores1 = [0.95, 0.87]
        scores2 = [0.92, 0.83]

        await cache.cache_reranking("query", doc_ids, "model1", scores1)
        await cache.cache_reranking("query", doc_ids, "model2", scores2)

        cached1 = await cache.get_reranking("query", doc_ids, "model1")
        cached2 = await cache.get_reranking("query", doc_ids, "model2")

        assert cached1 == scores1
        assert cached2 == scores2

    # Query transformation cache tests

    @pytest.mark.asyncio
    async def test_cache_and_get_query_transformation_string(
        self, cache: RAGCache
    ) -> None:
        """Test caching string query transformation."""
        original = "what is ai?"
        transformed = "What is artificial intelligence?"

        await cache.cache_query_transformation(
            original,
            "rewrite",
            transformed,
            {"model": "gpt-4"},
        )
        cached = await cache.get_query_transformation(
            original,
            "rewrite",
            {"model": "gpt-4"},
        )

        assert cached == transformed

    @pytest.mark.asyncio
    async def test_cache_and_get_query_transformation_list(
        self, cache: RAGCache
    ) -> None:
        """Test caching list query transformation."""
        original = "machine learning"
        transformed = ["machine learning", "ML algorithms", "supervised learning"]

        await cache.cache_query_transformation(
            original,
            "expansion",
            transformed,
            {"num": 3},
        )
        cached = await cache.get_query_transformation(
            original,
            "expansion",
            {"num": 3},
        )

        assert cached == transformed

    @pytest.mark.asyncio
    async def test_get_nonexistent_query_transformation(self, cache: RAGCache) -> None:
        """Test getting non-existent transformation returns None."""
        result = await cache.get_query_transformation("query", "rewrite")
        assert result is None
