"""Tests for query routing module."""

from __future__ import annotations

from lexigram.ai.rag.multimodal.types import Modality
import pytest
from lexigram.ai.rag.multimodal.types import Modality

import pytest

pytest.importorskip('lexigram.ai.rag', reason="lexigram-ai-rag not installed")

try:  # noqa: F401
    from lexigram.ai.rag.routing import (
        DataSourceProtocol,  # noqa: F401
        DataSourceType,  # noqa: F401
        HybridRouter,  # noqa: F401
        LLMRouter,  # noqa: F401
        QueryAnalyzer,  # noqa: F401
        QueryFeatures,  # noqa: F401
        QueryIntent,  # noqa: F401
        QueryRouter,  # noqa: F401
        RoutingDecision,  # noqa: F401
        RoutingPattern,  # noqa: F401
        RoutingRule,  # noqa: F401
        RoutingStatistics,  # noqa: F401
        RuleBasedRouter,  # noqa: F401
        SemanticRouter,  # noqa: F401
    )
except ImportError as e:
    pytest.skip(f"lexigram-ai-rag not installed: {e}", allow_module_level=True)


class TestRoutingDecision:
    """Test RoutingDecision dataclass."""

    def test_create_decision(self):
        """Test creating routing decision."""
        source = DataSourceProtocol(
            name="test",
            type=DataSourceType.VECTOR_STORE,
            description="Test",
        )

        decision = RoutingDecision(
            query="Test query",
            data_sources=[source],
            strategy="dense",
            confidence=0.9,
            reasoning="Test routing",
        )

        assert decision.query == "Test query"
        assert len(decision.data_sources) == 1
        assert decision.strategy == "dense"
        assert decision.confidence == 0.9

    def test_primary_source(self):
        """Test primary_source property."""
        source1 = DataSourceProtocol(
            name="s1", type=DataSourceType.VECTOR_STORE, description="S1",
        )
        source2 = DataSourceProtocol(
            name="s2", type=DataSourceType.KEYWORD_INDEX, description="S2",
        )

        decision = RoutingDecision(
            query="Test",
            data_sources=[source1, source2],
            strategy="hybrid",
            confidence=0.8,
            reasoning="Test",
        )

        assert decision.primary_source == source1

    def test_is_confident(self):
        """Test is_confident property."""
        decision = RoutingDecision(
            query="Test",
            data_sources=[],
            strategy="dense",
            confidence=0.8,
            reasoning="Test",
        )

        assert decision.is_confident is True

        decision.confidence = 0.5
        assert decision.is_confident is False

    def test_is_multimodal(self):
        """Test is_multimodal property."""
        multimodal_source = DataSourceProtocol(
            name="mm",
            type=DataSourceType.MULTIMODAL_STORE,
            description="Multimodal",
        )
        vector_source = DataSourceProtocol(
            name="vec",
            type=DataSourceType.VECTOR_STORE,
            description="Vector",
        )

        decision1 = RoutingDecision(
            query="Test",
            data_sources=[multimodal_source],
            strategy="multimodal",
            confidence=0.8,
            reasoning="Test",
        )
        assert decision1.is_multimodal is True

        decision2 = RoutingDecision(
            query="Test",
            data_sources=[vector_source],
            strategy="dense",
            confidence=0.8,
            reasoning="Test",
        )
        assert decision2.is_multimodal is False

    def test_to_dict(self):
        """Test to_dict method."""
        source = DataSourceProtocol(
            name="test",
            type=DataSourceType.VECTOR_STORE,
            description="Test source",
        )
        features = QueryFeatures(
            text="Test query",
            length=10,
            intent=QueryIntent.FACTUAL,
            modalities=[Modality.TEXT],
        )

        decision = RoutingDecision(
            query="Test query",
            data_sources=[source],
            strategy="dense",
            confidence=0.9,
            reasoning="Test",
            features=features,
        )

        result = decision.to_dict()

        assert result["query"] == "Test query"
        assert len(result["data_sources"]) == 1
        assert result["data_sources"][0]["name"] == "test"
        assert result["strategy"] == "dense"
        assert result["confidence"] == 0.9
        assert result["features"]["intent"] == "factual"


class TestQueryAnalyzer:
    """Test QueryAnalyzer class."""

    @pytest.mark.asyncio
    async def test_analyze_basic(self):
        """Test basic query analysis."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("What is Python?")

        assert features.text == "What is Python?"
        assert features.length == 15
        assert features.intent == QueryIntent.FACTUAL
        assert "python" in features.keywords

    @pytest.mark.asyncio
    async def test_classify_factual_intent(self):
        """Test factual intent classification."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("What is machine learning?")
        assert features.intent == QueryIntent.FACTUAL

    @pytest.mark.asyncio
    async def test_classify_procedural_intent(self):
        """Test procedural intent classification."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("How do I configure authentication?")
        assert features.intent == QueryIntent.PROCEDURAL

    @pytest.mark.asyncio
    async def test_classify_analytical_intent(self):
        """Test analytical intent classification."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("Compare Python vs Java")
        assert features.intent == QueryIntent.ANALYTICAL

    @pytest.mark.asyncio
    async def test_extract_keywords(self):
        """Test keyword extraction."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze(
            "How to configure database connection for authentication?",
        )

        assert "configure" in features.keywords
        assert "database" in features.keywords
        assert "connection" in features.keywords
        assert "authentication" in features.keywords

    @pytest.mark.asyncio
    async def test_detect_domain(self):
        """Test domain detection."""
        analyzer = QueryAnalyzer()

        # Technical domain
        features = await analyzer.analyze(
            "How to debug API function call in production server?",
        )
        assert features.domain == "technical"

    @pytest.mark.asyncio
    async def test_detect_entities(self):
        """Test entity detection."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("What did Albert Einstein discover?")
        assert features.has_entities is True

    @pytest.mark.asyncio
    async def test_detect_modalities(self):
        """Test modality detection."""
        analyzer = QueryAnalyzer()

        # Image modality
        features = await analyzer.analyze("Show me images of sunset")
        assert Modality.IMAGE in features.modalities

        # Video modality
        features = await analyzer.analyze("Find videos about cooking")
        assert Modality.VIDEO in features.modalities

        # Audio modality
        features = await analyzer.analyze("Play audio recording of birds")
        assert Modality.AUDIO in features.modalities

    @pytest.mark.asyncio
    async def test_calculate_complexity(self):
        """Test complexity calculation."""
        analyzer = QueryAnalyzer()

        # Simple query
        features = await analyzer.analyze("What is AI?")
        assert features.complexity < 0.5

        # Complex query
        complex_query = "Compare the differences between supervised and unsupervised machine learning algorithms, considering performance, data requirements, and computational complexity across various use cases"
        features = await analyzer.analyze(complex_query)
        assert features.complexity > 0.5
