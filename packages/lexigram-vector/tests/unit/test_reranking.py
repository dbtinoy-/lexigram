"""Tests for reranking module."""

from __future__ import annotations

import pytest

from lexigram.contracts.ai.vector import Document, RAGSearchResult
from lexigram.vector.search.reranking import (
    CrossEncoderReranker,
    CustomReranker,
    DiversityReranker,
    RerankerPipeline,
    RerankingConfig,
    RerankingStrategy,
    SimilarityReranker,
    create_reranker,
)


# Test fixtures
@pytest.fixture
def sample_results():
    """Sample search results for testing."""
    return [
        RAGSearchResult(
            document=Document(id="1", text="Python is a programming language"),
            score=0.9,
            rank=0,
        ),
        RAGSearchResult(
            document=Document(id="2", text="Java is also a programming language"),
            score=0.8,
            rank=1,
        ),
        RAGSearchResult(
            document=Document(id="3", text="Python programming tutorials"),
            score=0.7,
            rank=2,
        ),
        RAGSearchResult(
            document=Document(id="4", text="Machine learning with Python"),
            score=0.6,
            rank=3,
        ),
    ]


class TestSimilarityReranker:
    """Test similarity-based reranking."""

    @pytest.mark.asyncio
    async def test_basic_reranking(self, sample_results):
        """Test basic reranking."""
        reranker = SimilarityReranker()
        results = await reranker.rerank("Python programming", sample_results)
        assert len(results) == 4
        # All results should be re-ranked
        assert all(r.rank == i for i, r in enumerate(results))

    @pytest.mark.asyncio
    async def test_exact_match_boost(self, sample_results):
        """Test exact match boost."""
        reranker = SimilarityReranker(exact_match_boost=1.0)
        results = await reranker.rerank("Python programming", sample_results)
        # Documents with exact "Python programming" match should rank higher
        assert len(results) == 4

    @pytest.mark.asyncio
    async def test_top_k_limiting(self, sample_results):
        """Test top_k limiting."""
        reranker = SimilarityReranker()
        results = await reranker.rerank("Python", sample_results, top_k=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """Test empty results."""
        reranker = SimilarityReranker()
        results = await reranker.rerank("Python", [])
        assert len(results) == 0


class TestDiversityReranker:
    """Test diversity-based reranking."""

    @pytest.mark.asyncio
    async def test_basic_diversity(self, sample_results):
        """Test basic diversity reranking."""
        reranker = DiversityReranker(lambda_param=0.7)
        results = await reranker.rerank("Python programming", sample_results)
        assert len(results) == 4

    @pytest.mark.asyncio
    async def test_top_k_limiting(self, sample_results):
        """Test top_k limiting."""
        reranker = DiversityReranker()
        results = await reranker.rerank("Python", sample_results, top_k=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """Test empty results."""
        reranker = DiversityReranker()
        results = await reranker.rerank("Python", [])
        assert len(results) == 0


class TestCustomReranker:
    """Test custom reranking."""

    @pytest.mark.asyncio
    async def test_custom_scoring(self, sample_results):
        """Test custom scoring function."""

        def length_scorer(query: str, doc: Document) -> float:
            return len(doc.text) / 100.0

        reranker = CustomReranker(score_fn=length_scorer, combine_scores=False)
        results = await reranker.rerank("Python", sample_results)

        assert len(results) == 4
        # Longer documents should rank higher
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    @pytest.mark.asyncio
    async def test_combine_scores(self, sample_results):
        """Test combining custom and original scores."""

        def constant_scorer(query: str, doc: Document) -> float:
            return 0.5

        reranker = CustomReranker(
            score_fn=constant_scorer,
            combine_scores=True,
            weight=0.5,
        )
        results = await reranker.rerank("Python", sample_results)
        assert len(results) == 4


class TestRerankingConfig:
    """Test RerankingConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = RerankingConfig()
        assert config.strategy == RerankingStrategy.SIMILARITY
        assert config.score_boost == 0.1
        assert config.lambda_param == 0.7
        assert config.top_k is None

    def test_custom_config(self):
        """Test custom configuration."""
        config = RerankingConfig(
            strategy=RerankingStrategy.DIVERSITY,
            score_boost=0.2,
            lambda_param=0.5,
            top_k=5,
        )
        assert config.strategy == RerankingStrategy.DIVERSITY
        assert config.score_boost == 0.2
        assert config.lambda_param == 0.5
        assert config.top_k == 5

    def test_validation(self):
        """Test configuration validation."""
        # Lambda must be 0-1
        with pytest.raises(ValueError):
            RerankingConfig(lambda_param=1.5)

        # Negative boost
        with pytest.raises(ValueError):
            RerankingConfig(score_boost=-0.1)

        # Zero top_k
        with pytest.raises(ValueError):
            RerankingConfig(top_k=0)


class TestCreateReranker:
    """Test reranker factory function."""

    def test_create_similarity(self):
        """Test creating similarity reranker."""
        reranker = create_reranker(RerankingStrategy.SIMILARITY)
        assert isinstance(reranker, SimilarityReranker)

    def test_create_diversity(self):
        """Test creating diversity reranker."""
        reranker = create_reranker(RerankingStrategy.DIVERSITY)
        assert isinstance(reranker, DiversityReranker)

    def test_create_custom(self):
        """Test creating custom reranker."""

        def my_scorer(q: str, d: Document) -> float:
            return 1.0

        reranker = create_reranker(RerankingStrategy.CUSTOM, score_fn=my_scorer)
        assert isinstance(reranker, CustomReranker)

    def test_create_custom_without_fn(self):
        """Test creating custom reranker without score function."""
        with pytest.raises(ValueError, match="requires 'score_fn'"):
            create_reranker(RerankingStrategy.CUSTOM)

    def test_create_cross_encoder(self):
        """Test creating cross-encoder (should fail)."""
        with pytest.raises(NotImplementedError, match="current version"):
            create_reranker(RerankingStrategy.CROSS_ENCODER)

    def test_create_with_config(self):
        """Test creating with configuration."""
        config = RerankingConfig(score_boost=0.3)
        reranker = create_reranker(config=config)

        assert isinstance(reranker, SimilarityReranker)
        assert reranker.score_boost == 0.3

    def test_create_with_kwargs(self):
        """Test creating with keyword arguments."""
        reranker = create_reranker(
            RerankingStrategy.SIMILARITY,
            score_boost=0.25,
            exact_match_boost=0.75,
        )

        assert isinstance(reranker, SimilarityReranker)
        assert reranker.score_boost == 0.25
        assert reranker.exact_match_boost == 0.75


class TestRerankerPipeline:
    """Test reranker pipeline."""

    @pytest.mark.asyncio
    async def test_single_reranker(self, sample_results):
        """Test pipeline with single reranker."""
        pipeline = RerankerPipeline([SimilarityReranker()])
        results = await pipeline.rerank("Python", sample_results)

        assert len(results) == 4

    @pytest.mark.asyncio
    async def test_multiple_rerankers(self, sample_results):
        """Test pipeline with multiple rerankers."""
        pipeline = RerankerPipeline(
            [
                SimilarityReranker(score_boost=0.1),
                DiversityReranker(lambda_param=0.5),
            ],
        )
        results = await pipeline.rerank("Python programming", sample_results)

        assert len(results) == 4
        # Should apply both rerankers in sequence

    @pytest.mark.asyncio
    async def test_pipeline_top_k(self, sample_results):
        """Test pipeline with top-k."""
        pipeline = RerankerPipeline(
            [
                SimilarityReranker(),
                DiversityReranker(),
            ],
        )
        results = await pipeline.rerank("Python", sample_results, top_k=2)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_empty_pipeline(self, sample_results):
        """Test pipeline with no rerankers."""
        pipeline = RerankerPipeline([])
        results = await pipeline.rerank("Python", sample_results)

        # Should return original results
        assert len(results) == 4


class TestIntegration:
    """Integration tests for reranking."""

    @pytest.mark.asyncio
    async def test_similarity_then_diversity(self, sample_results):
        """Test similarity followed by diversity."""
        # First boost by similarity
        sim_reranker = SimilarityReranker(score_boost=0.5)
        sim_results = await sim_reranker.rerank("Python programming", sample_results)

        # Then diversify
        div_reranker = DiversityReranker(lambda_param=0.5)
        final_results = await div_reranker.rerank("Python programming", sim_results)

        assert len(final_results) == 4
        # Should have both relevance and diversity

    @pytest.mark.asyncio
    async def test_real_world_scenario(self):
        """Test realistic reranking scenario."""
        # Search results from hypothetical search
        results = [
            RAGSearchResult(
                document=Document(
                    id="1",
                    text="Python tutorial for beginners - learn Python programming",
                ),
                score=0.85,
                rank=0,
            ),
            RAGSearchResult(
                document=Document(
                    id="2",
                    text="Python programming guide for experts",
                ),
                score=0.82,
                rank=1,
            ),
            RAGSearchResult(
                document=Document(
                    id="3",
                    text="Advanced Python techniques and best practices",
                ),
                score=0.80,
                rank=2,
            ),
            RAGSearchResult(
                document=Document(
                    id="4",
                    text="Machine learning with Python and scikit-learn",
                ),
                score=0.75,
                rank=3,
            ),
            RAGSearchResult(
                document=Document(
                    id="5",
                    text="Data science tools and libraries",
                ),
                score=0.70,
                rank=4,
            ),
        ]

        # Create pipeline: similarity boost -> diversity
        pipeline = RerankerPipeline(
            [
                SimilarityReranker(score_boost=0.2, exact_match_boost=0.3),
                DiversityReranker(lambda_param=0.6),
            ],
        )

        final_results = await pipeline.rerank("Python programming", results, top_k=3)

        assert len(final_results) == 3
        # First result should be highly relevant
        assert "python" in final_results[0].document.text.lower()
        assert "programming" in final_results[0].document.text.lower()
