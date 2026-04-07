"""Tests for hybrid search and BM25 retrieval."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.contracts.ai.vector import Document, RAGSearchResult
from lexigram.vector.search.hybrid import (
    BM25Retriever,
    BM25Scorer,
    HybridRetriever,
    HybridSearchConfig,
    RRFReranker,
    SimpleTokenizer,
    create_hybrid_retriever,
)

SearchResult = RAGSearchResult


class TestSimpleTokenizer:
    """Tests for SimpleTokenizer."""

    def test_basic_tokenization(self):
        """Test basic tokenization."""
        tokenizer = SimpleTokenizer()
        tokens = tokenizer.tokenize("Hello, world!")
        assert tokens == ["hello", "world"]

    def test_lowercase(self):
        """Test lowercase normalization."""
        tokenizer = SimpleTokenizer(lowercase=True)
        tokens = tokenizer.tokenize("Python Programming")
        assert tokens == ["python", "programming"]

    def test_no_lowercase(self):
        """Test without lowercase normalization."""
        tokenizer = SimpleTokenizer(lowercase=False)
        tokens = tokenizer.tokenize("Python Programming")
        assert tokens == ["Python", "Programming"]

    def test_punctuation_removal(self):
        """Test punctuation removal."""
        tokenizer = SimpleTokenizer(remove_punctuation=True)
        tokens = tokenizer.tokenize("hello, world! how are you?")
        assert tokens == ["hello", "world", "how", "are", "you"]

    def test_empty_string(self):
        """Test empty string."""
        tokenizer = SimpleTokenizer()
        tokens = tokenizer.tokenize("")
        assert tokens == []

    def test_multiple_spaces(self):
        """Test multiple spaces."""
        tokenizer = SimpleTokenizer()
        tokens = tokenizer.tokenize("hello    world")
        assert tokens == ["hello", "world"]


class TestBM25Scorer:
    """Tests for BM25Scorer."""

    def test_basic_scoring(self):
        """Test basic BM25 scoring."""
        scorer = BM25Scorer()
        docs = [
            ["hello", "world"],
            ["hello", "python"],
            ["world", "programming"],
        ]
        scorer.fit(docs)

        # Query "hello" should match first two docs
        score1 = scorer.score(["hello"], 0, docs[0])
        score2 = scorer.score(["hello"], 1, docs[1])
        score3 = scorer.score(["hello"], 2, docs[2])

        assert score1 > 0
        assert score2 > 0
        assert score3 == 0  # "hello" not in third doc

    def test_idf_calculation(self):
        """Test IDF score calculation."""
        scorer = BM25Scorer()
        docs = [
            ["rare", "term"],
            ["common", "term"],
            ["common", "term"],
        ]
        scorer.fit(docs)

        # "rare" appears in 1 doc, "common" in 2 docs
        # IDF for "rare" should be higher
        assert scorer.idf_scores["rare"] > scorer.idf_scores["common"]

    def test_term_frequency_saturation(self):
        """Test term frequency saturation with k1."""
        scorer = BM25Scorer(k1=1.5)
        docs = [
            ["term"] * 10,  # High frequency
            ["term"],  # Low frequency
        ]
        scorer.fit(docs)

        score_high_tf = scorer.score(["term"], 0, docs[0])
        score_low_tf = scorer.score(["term"], 1, docs[1])

        # Higher TF should give higher score, but saturated
        assert score_high_tf > score_low_tf
        # But not 10x higher due to saturation
        assert score_high_tf < score_low_tf * 10

    def test_length_normalization(self):
        """Test document length normalization with b."""
        scorer = BM25Scorer(b=0.75)
        docs = [
            ["term"] + ["other"] * 100,  # Long document
            ["term"],  # Short document
        ]
        scorer.fit(docs)

        score_long = scorer.score(["term"], 0, docs[0])
        score_short = scorer.score(["term"], 1, docs[1])

        # Length normalization should penalize longer docs
        assert score_short > score_long


class TestBM25Retriever:
    """Tests for BM25Retriever."""

    def test_add_and_search(self):
        """Test adding documents and searching."""
        retriever = BM25Retriever()

        docs = [
            Document(id="1", text="Python is a programming language"),
            Document(id="2", text="Java is also a programming language"),
            Document(id="3", text="Python is popular for data science"),
        ]
        retriever.add_documents(docs)

        results = retriever.search("python", k=5)

        assert len(results) == 2  # Should find 2 docs with "python"
        assert all(isinstance(r, RAGSearchResult) for r in results)
        assert results[0].rank == 0
        assert results[1].rank == 1

    def test_search_ranking(self):
        """Test that results are properly ranked."""
        retriever = BM25Retriever()

        docs = [
            Document(id="1", text="python python python"),  # High relevance
            Document(id="2", text="python"),  # Medium relevance
            Document(id="3", text="java"),  # No relevance
        ]
        retriever.add_documents(docs)

        results = retriever.search("python", k=5)

        assert len(results) == 2
        # Doc with more occurrences should rank higher
        assert results[0].document.id == "1"
        assert results[1].document.id == "2"
        assert results[0].score > results[1].score

    def test_multi_term_query(self):
        """Test multi-term queries."""
        retriever = BM25Retriever()

        docs = [
            Document(id="1", text="python programming language"),
            Document(id="2", text="python data science"),
            Document(id="3", text="java programming language"),
        ]
        retriever.add_documents(docs)

        results = retriever.search("python programming", k=5)

        # Doc 1 has both terms, should rank highest
        assert results[0].document.id == "1"

    def test_min_score_threshold(self):
        """Test minimum score threshold."""
        retriever = BM25Retriever()

        docs = [
            Document(id="1", text="python programming"),
            Document(id="2", text="python"),
        ]
        retriever.add_documents(docs)

        # High threshold should filter results
        results = retriever.search("python", k=5, min_score=100.0)
        assert len(results) == 0

    def test_empty_query(self):
        """Test empty query."""
        retriever = BM25Retriever()
        retriever.add_documents([Document(id="1", text="test")])

        results = retriever.search("", k=5)
        assert len(results) == 0

    def test_no_documents(self):
        """Test search with no documents."""
        retriever = BM25Retriever()
        results = retriever.search("python", k=5)
        assert len(results) == 0

    def test_clear(self):
        """Test clearing documents."""
        retriever = BM25Retriever()
        retriever.add_documents([Document(id="1", text="test")])

        assert len(retriever.documents) == 1

        retriever.clear()
        assert len(retriever.documents) == 0
        assert len(retriever.tokenized_docs) == 0


class TestRRFReranker:
    """Tests for RRFReranker."""

    def test_basic_fusion(self):
        """Test basic RRF fusion."""
        reranker = RRFReranker(k=60)

        # Create two ranked lists
        list1 = [
            RAGSearchResult(document=Document(id="1", text="doc1"), score=1.0, rank=0),
            RAGSearchResult(document=Document(id="2", text="doc2"), score=0.8, rank=1),
        ]
        list2 = [
            RAGSearchResult(document=Document(id="2", text="doc2"), score=0.9, rank=0),
            RAGSearchResult(document=Document(id="3", text="doc3"), score=0.7, rank=1),
        ]

        fused = reranker.fuse([list1, list2])

        # Doc 2 appears in both lists and rank 0 in list2, should rank high
        assert len(fused) == 3
        assert all(isinstance(r, RAGSearchResult) for r in fused)

    def test_weighted_fusion(self):
        """Test weighted RRF fusion."""
        reranker = RRFReranker(k=60)

        list1 = [
            RAGSearchResult(document=Document(id="1", text="doc1"), score=1.0, rank=0),
        ]
        list2 = [
            RAGSearchResult(document=Document(id="2", text="doc2"), score=1.0, rank=0),
        ]

        # Give list1 higher weight
        fused = reranker.fuse([list1, list2], weights=[2.0, 1.0])

        # Doc from list1 should rank higher due to weight
        assert fused[0].document.id == "1"

    def test_empty_lists(self):
        """Test fusion with empty lists."""
        reranker = RRFReranker()
        fused = reranker.fuse([])
        assert len(fused) == 0

    def test_single_list(self):
        """Test fusion with single list."""
        reranker = RRFReranker()

        list1 = [
            RAGSearchResult(document=Document(id="1", text="doc1"), score=1.0, rank=0),
            RAGSearchResult(document=Document(id="2", text="doc2"), score=0.8, rank=1),
        ]

        fused = reranker.fuse([list1])

        assert len(fused) == 2
        assert fused[0].document.id == "1"

    def test_weight_validation(self):
        """Test weight validation."""
        reranker = RRFReranker()

        list1 = [
            RAGSearchResult(document=Document(id="1", text="doc1"), score=1.0, rank=0),
        ]
        list2 = [
            RAGSearchResult(document=Document(id="2", text="doc2"), score=1.0, rank=0),
        ]

        # Wrong number of weights should raise error
        with pytest.raises(ValueError):
            reranker.fuse([list1, list2], weights=[1.0])


class MockVectorStore:
    """Mock vector store for testing hybrid retriever."""

    def __init__(self) -> None:
        self.documents: list[Document] = []

    async def search(
        self, query: str, k: int = 10, filter: Any = None
    ) -> list[RAGSearchResult]:
        """Mock search returning first k documents."""
        results = []
        for rank, doc in enumerate(self.documents[:k]):
            # Simple mock scoring based on query in text
            score = 0.9 if query.lower() in doc.text.lower() else 0.5
            results.append(RAGSearchResult(document=doc, score=score, rank=rank))
        return results

    def add_documents(self, documents: list[Document]) -> None:
        """Add documents."""
        self.documents.extend(documents)


class TestHybridRetriever:
    """Tests for HybridRetriever."""

    @pytest.mark.asyncio
    async def test_basic_hybrid_search(self):
        """Test basic hybrid search."""
        vector_store = MockVectorStore()
        retriever = HybridRetriever(vector_store=vector_store)

        docs = [
            Document(id="1", text="python programming language"),
            Document(id="2", text="java programming language"),
            Document(id="3", text="python data science"),
        ]

        # Add to both stores
        await retriever.add_documents(docs)
        vector_store.add_documents(docs)

        results = await retriever.search("python", k=5)

        assert len(results) > 0
        assert all(isinstance(r, RAGSearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_hybrid_with_weights(self):
        """Test hybrid search with different weights."""
        vector_store = MockVectorStore()

        # BM25 heavy
        retriever1 = HybridRetriever(
            vector_store=vector_store,
            bm25_weight=0.9,
            vector_weight=0.1,
        )

        # Vector heavy
        retriever2 = HybridRetriever(
            vector_store=vector_store,
            bm25_weight=0.1,
            vector_weight=0.9,
        )

        docs = [Document(id="1", text="test document")]
        await retriever1.add_documents(docs)
        await retriever2.add_documents(docs)
        vector_store.add_documents(docs)

        results1 = await retriever1.search("test", k=5)
        results2 = await retriever2.search("test", k=5)

        assert len(results1) > 0
        assert len(results2) > 0

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing BM25 index."""
        vector_store = MockVectorStore()
        retriever = HybridRetriever(vector_store=vector_store)

        docs = [Document(id="1", text="test")]
        await retriever.add_documents(docs)

        assert len(retriever.bm25_retriever.documents) == 1

        retriever.clear()
        assert len(retriever.bm25_retriever.documents) == 0


class TestHybridSearchConfig:
    """Tests for HybridSearchConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = HybridSearchConfig()

        assert config.bm25_weight == 0.5
        assert config.vector_weight == 0.5
        assert config.rrf_k == 60
        assert config.bm25_k1 == 1.5
        assert config.bm25_b == 0.75

    def test_custom_config(self):
        """Test custom configuration."""
        config = HybridSearchConfig(
            bm25_weight=0.6,
            vector_weight=0.4,
            rrf_k=100,
        )

        assert config.bm25_weight == 0.6
        assert config.vector_weight == 0.4
        assert config.rrf_k == 100

    def test_weight_validation(self):
        """Test weight validation."""
        # Weights should be between 0 and 1
        with pytest.raises(ValueError):
            HybridSearchConfig(bm25_weight=-0.1)

        with pytest.raises(ValueError):
            HybridSearchConfig(bm25_weight=1.5)


class TestCreateHybridRetriever:
    """Tests for create_hybrid_retriever factory."""

    def test_default_creation(self):
        """Test creation with default config."""
        vector_store = MockVectorStore()
        retriever = create_hybrid_retriever(vector_store)

        assert isinstance(retriever, HybridRetriever)
        assert retriever.bm25_weight == 0.5
        assert retriever.vector_weight == 0.5

    def test_custom_config_creation(self):
        """Test creation with custom config."""
        vector_store = MockVectorStore()
        config = HybridSearchConfig(bm25_weight=0.7, vector_weight=0.3)
        retriever = create_hybrid_retriever(vector_store, config)

        assert retriever.bm25_weight == 0.7
        assert retriever.vector_weight == 0.3


class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete hybrid search workflow."""
        # Setup
        vector_store = MockVectorStore()
        retriever = HybridRetriever(vector_store=vector_store)

        # Add documents
        docs = [
            Document(id="1", text="Python is a programming language for data science"),
            Document(id="2", text="Java is a programming language for enterprise"),
            Document(id="3", text="Python has great libraries for machine learning"),
            Document(id="4", text="JavaScript is used for web development"),
        ]
        await retriever.add_documents(docs)
        vector_store.add_documents(docs)

        # Search
        results = await retriever.search("python programming", k=3)

        # Verify results
        assert len(results) <= 3
        assert all(r.rank < len(results) for r in results)

        # Documents with "python" should rank high
        top_doc_ids = list(map(lambda r: r.document.id, results))
        assert "1" in top_doc_ids or "3" in top_doc_ids
