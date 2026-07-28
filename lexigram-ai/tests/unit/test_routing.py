"""Tests for query routing module."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")


from unittest.mock import AsyncMock

import numpy as np

from lexigram.ai.rag.multimodal.types import Modality
try:
    from lexigram.ai.rag.routing import (
        DataSourceProtocol,
        DataSourceType,
        HybridRouter,
        LLMRouter,
        QueryAnalyzer,
        QueryFeatures,
        QueryIntent,
        QueryRouter,
        RoutingDecision,
        RoutingPattern,
        RoutingRule,
        RoutingStatistics,
        RuleBasedRouter,
        SemanticRouter,
    )
except ImportError as e:
    pytest.skip(f"routing import failed: {e}", allow_module_level=True)


class TestQueryIntent:
    """Test QueryIntent enum."""

    def test_intent_values(self):
        """Test all intent values."""
        assert QueryIntent.FACTUAL.value == "factual"
        assert QueryIntent.CONVERSATIONAL.value == "conversational"
        assert QueryIntent.ANALYTICAL.value == "analytical"
        assert QueryIntent.CREATIVE.value == "creative"
        assert QueryIntent.PROCEDURAL.value == "procedural"
        assert QueryIntent.NAVIGATIONAL.value == "navigational"


class TestDataSourceType:
    """Test DataSourceType enum."""

    def test_source_types(self):
        """Test all source type values."""
        assert DataSourceType.VECTOR_STORE.value == "vector_store"
        assert DataSourceType.KEYWORD_INDEX.value == "keyword_index"
        assert DataSourceType.KNOWLEDGE_GRAPH.value == "knowledge_graph"
        assert DataSourceType.SQL_DATABASE.value == "sql_database"
        assert DataSourceType.EXTERNAL_API.value == "external_api"
        assert DataSourceType.MULTIMODAL_STORE.value == "multimodal_store"


class TestQueryFeatures:
    """Test QueryFeatures dataclass."""

    def test_create_features(self):
        """Test creating query features."""
        features = QueryFeatures(
            text="What is Python?",
            length=15,
            intent=QueryIntent.FACTUAL,
            keywords=["python"],
        )

        assert features.text == "What is Python?"
        assert features.length == 15
        assert features.intent == QueryIntent.FACTUAL
        assert features.keywords == ["python"]

    def test_is_simple(self):
        """Test is_simple property."""
        features = QueryFeatures(
            text="Test",
            length=4,
            intent=QueryIntent.FACTUAL,
            complexity=0.2,
        )
        assert features.is_simple is True

        features.complexity = 0.5
        assert features.is_simple is False

    def test_is_complex(self):
        """Test is_complex property."""
        features = QueryFeatures(
            text="Test",
            length=4,
            intent=QueryIntent.FACTUAL,
            complexity=0.8,
        )
        assert features.is_complex is True

        features.complexity = 0.5
        assert features.is_complex is False

    def test_is_multimodal(self):
        """Test is_multimodal property."""
        features = QueryFeatures(
            text="Test",
            length=4,
            intent=QueryIntent.FACTUAL,
            modalities=[Modality.TEXT, Modality.IMAGE],
        )
        assert features.is_multimodal is True

        features.modalities = [Modality.TEXT]
        assert features.is_multimodal is False

    def test_is_long(self):
        """Test is_long property."""
        features = QueryFeatures(
            text="A" * 250,
            length=250,
            intent=QueryIntent.FACTUAL,
        )
        assert features.is_long is True

        features.length = 100
        assert features.is_long is False


class TestDataSource:
    """Test DataSourceProtocol dataclass."""

    def test_create_source(self):
        """Test creating data source."""
        source = DataSourceProtocol(
            name="vector_db",
            type=DataSourceType.VECTOR_STORE,
            description="Vector database",
            capabilities=["dense_search", "semantic_search"],
            priority=10,
        )

        assert source.name == "vector_db"
        assert source.type == DataSourceType.VECTOR_STORE
        assert source.description == "Vector database"
        assert "dense_search" in source.capabilities

    def test_supports(self):
        """Test supports method."""
        source = DataSourceProtocol(
            name="test",
            type=DataSourceType.VECTOR_STORE,
            description="Test",
            capabilities=["dense_search", "semantic_search"],
        )

        assert source.supports("dense_search") is True
        assert source.supports("keyword_search") is False

    def test_equality(self):
        """Test equality based on name."""
        source1 = DataSourceProtocol(
            name="test",
            type=DataSourceType.VECTOR_STORE,
            description="Test 1",
        )
        source2 = DataSourceProtocol(
            name="test",
            type=DataSourceType.KEYWORD_INDEX,
            description="Test 2",
        )
        source3 = DataSourceProtocol(
            name="different",
            type=DataSourceType.VECTOR_STORE,
            description="Test 3",
        )

        assert source1 == source2  # Same name
        assert source1 != source3  # Different name

    def test_hashable(self):
        """Test DataSourceProtocol is hashable."""
        source = DataSourceProtocol(
            name="test",
            type=DataSourceType.VECTOR_STORE,
            description="Test",
        )

        # Should be able to use in set/dict
        sources_set = {source}
        assert source in sources_set


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


class TestRuleBasedRouter:
    """Test RuleBasedRouter class."""

    @pytest.mark.asyncio
    async def test_create_router(self):
        """Test creating router with default rules."""
        router = RuleBasedRouter()
        assert len(router.rules) > 0

    @pytest.mark.asyncio
    async def test_add_custom_rule(self):
        """Test adding custom rule."""
        router = RuleBasedRouter(use_default_rules=False)

        rule = RoutingRule(
            name="test_rule",
            condition=lambda f: f.length > 100,
            data_source_types=[DataSourceType.VECTOR_STORE],
            strategy="dense",
            priority=10,
        )

        router.add_rule(rule)
        assert len(router.rules) == 1
        assert router.rules[0].name == "test_rule"

    @pytest.mark.asyncio
    async def test_remove_rule(self):
        """Test removing rule."""
        router = RuleBasedRouter(use_default_rules=False)

        rule = RoutingRule(
            name="test_rule",
            condition=lambda f: True,
            data_source_types=[DataSourceType.VECTOR_STORE],
            strategy="dense",
        )

        router.add_rule(rule)
        assert router.remove_rule("test_rule") is True
        assert router.remove_rule("nonexistent") is False

    @pytest.mark.asyncio
    async def test_route_multimodal_image(self):
        """Test routing multimodal image query."""
        router = RuleBasedRouter()

        features = QueryFeatures(
            text="Show me images",
            length=14,
            intent=QueryIntent.NAVIGATIONAL,
            modalities=[Modality.TEXT, Modality.IMAGE],
        )

        multimodal_source = DataSourceProtocol(
            name="mm_store",
            type=DataSourceType.MULTIMODAL_STORE,
            description="Multimodal store",
        )

        decision = await router.route(features, [multimodal_source])

        assert decision.strategy == "multimodal"
        assert decision.data_sources[0] == multimodal_source
        assert decision.confidence > 0.8

    @pytest.mark.asyncio
    async def test_route_analytical_query(self):
        """Test routing analytical query."""
        router = RuleBasedRouter()

        features = QueryFeatures(
            text="Compare A and B",
            length=14,
            intent=QueryIntent.ANALYTICAL,
        )

        graph_source = DataSourceProtocol(
            name="kg",
            type=DataSourceType.KNOWLEDGE_GRAPH,
            description="Knowledge graph",
        )
        vector_source = DataSourceProtocol(
            name="vec",
            type=DataSourceType.VECTOR_STORE,
            description="Vector store",
        )

        decision = await router.route(features, [graph_source, vector_source])

        assert decision.strategy == "hybrid"
        assert graph_source in decision.data_sources

    @pytest.mark.asyncio
    async def test_route_fallback(self):
        """Test fallback routing when no rule matches."""
        router = RuleBasedRouter(use_default_rules=False)

        features = QueryFeatures(
            text="Test query",
            length=10,
            intent=QueryIntent.FACTUAL,
        )

        vector_source = DataSourceProtocol(
            name="vec",
            type=DataSourceType.VECTOR_STORE,
            description="Vector store",
        )

        decision = await router.route(features, [vector_source])

        assert decision.data_sources[0] == vector_source
        assert decision.strategy == "dense_search"
        assert decision.confidence == 0.5


class TestSemanticRouter:
    """Test SemanticRouter class."""

    @pytest.mark.asyncio
    async def test_create_router(self):
        """Test creating semantic router."""

        async def mock_embed(text):
            return np.random.rand(512)

        router = SemanticRouter(embed_fn=mock_embed)
        assert router.embed_fn is not None
        assert len(router.patterns) > 0  # Default patterns

    @pytest.mark.asyncio
    async def test_add_pattern(self):
        """Test adding routing pattern."""

        async def mock_embed(text):
            return np.random.rand(512)

        router = SemanticRouter(embed_fn=mock_embed, use_default_patterns=False)

        pattern = RoutingPattern(
            name="test_pattern",
            examples=["Example 1", "Example 2"],
            data_source_types=[DataSourceType.VECTOR_STORE],
            strategy="dense",
        )

        await router.add_pattern(pattern)
        assert len(router.patterns) == 1
        assert router.patterns[0].embedding is not None

    @pytest.mark.asyncio
    async def test_remove_pattern(self):
        """Test removing pattern."""
        router = SemanticRouter(use_default_patterns=False)

        pattern = RoutingPattern(
            name="test",
            examples=[],
            data_source_types=[DataSourceType.VECTOR_STORE],
            strategy="dense",
        )
        router.patterns.append(pattern)

        assert router.remove_pattern("test") is True
        assert router.remove_pattern("nonexistent") is False

    @pytest.mark.asyncio
    async def test_route_with_pattern_match(self):
        """Test routing with pattern matching."""

        # Mock embedding function that returns similar embeddings
        async def mock_embed(text):
            if "technical" in text.lower() or "api" in text.lower():
                return np.array([1.0] * 512)
            return np.array([0.0] * 512)

        router = SemanticRouter(
            embed_fn=mock_embed, use_default_patterns=False, similarity_threshold=0.9,
        )

        # Add pattern
        pattern = RoutingPattern(
            name="technical",
            examples=["How to use the API?"],
            data_source_types=[DataSourceType.VECTOR_STORE],
            strategy="dense",
        )
        await router.add_pattern(pattern)

        # Route similar query
        features = QueryFeatures(
            text="Technical API documentation",
            length=27,
            intent=QueryIntent.FACTUAL,
        )

        vector_source = DataSourceProtocol(
            name="vec",
            type=DataSourceType.VECTOR_STORE,
            description="Vector store",
        )

        decision = await router.route(features, [vector_source])

        # With high similarity threshold and matching embedding, should match pattern
        assert decision.data_sources[0] == vector_source

    @pytest.mark.asyncio
    async def test_route_fallback(self):
        """Test fallback routing when no pattern matches."""

        async def mock_embed(text):
            return np.random.rand(512)

        router = SemanticRouter(embed_fn=mock_embed, similarity_threshold=0.99)

        features = QueryFeatures(
            text="Random query",
            length=12,
            intent=QueryIntent.FACTUAL,
        )

        vector_source = DataSourceProtocol(
            name="vec",
            type=DataSourceType.VECTOR_STORE,
            description="Vector store",
        )

        decision = await router.route(features, [vector_source])

        assert decision.data_sources[0] == vector_source
        assert decision.metadata.get("fallback") is True


class TestLLMRouter:
    """Test LLMRouter class."""

    @pytest.mark.asyncio
    async def test_create_router(self):
        """Test creating LLM router."""

        async def mock_llm(prompt):
            return '{"data_source_names": ["vec"], "strategy": "dense", "confidence": 0.9, "reasoning": "Test"}'

        router = LLMRouter(llm_fn=mock_llm)
        assert router.llm_fn is not None

    @pytest.mark.asyncio
    async def test_route_with_llm(self):
        """Test routing with LLM."""

        async def mock_llm(prompt):
            return '{"data_source_names": ["vec"], "strategy": "dense", "confidence": 0.9, "reasoning": "LLM decision"}'

        router = LLMRouter(llm_fn=mock_llm)

        features = QueryFeatures(
            text="Test query",
            length=10,
            intent=QueryIntent.FACTUAL,
        )

        vector_source = DataSourceProtocol(
            name="vec",
            type=DataSourceType.VECTOR_STORE,
            description="Vector store",
        )

        decision = await router.route(features, [vector_source])

        assert decision.data_sources[0] == vector_source
        assert decision.strategy == "dense"
        assert decision.confidence == 0.9

    @pytest.mark.asyncio
    async def test_route_fallback_on_error(self):
        """Test fallback routing when LLM fails."""

        async def mock_llm(prompt):
            raise OSError("LLM error")

        router = LLMRouter(llm_fn=mock_llm)

        features = QueryFeatures(
            text="Test query",
            length=10,
            intent=QueryIntent.FACTUAL,
        )

        vector_source = DataSourceProtocol(
            name="vec",
            type=DataSourceType.VECTOR_STORE,
            description="Vector store",
        )

        decision = await router.route(features, [vector_source])

        assert decision.data_sources[0] == vector_source
        assert decision.metadata.get("fallback") is True


class TestHybridRouter:
    """Test HybridRouter class."""

    @pytest.mark.asyncio
    async def test_create_router(self):
        """Test creating hybrid router."""
        router = HybridRouter(strategies=[])
        assert len(router.strategies) == 0

    @pytest.mark.asyncio
    async def test_add_strategy(self):
        """Test adding strategy."""
        router = HybridRouter()
        strategy = RuleBasedRouter()
        router.add_strategy(strategy)
        assert len(router.strategies) == 1

    @pytest.mark.asyncio
    async def test_cascade_routing(self):
        """Test cascade routing (try in order)."""
        # Create strategies with different confidence levels
        low_confidence_strategy = AsyncMock()
        low_confidence_strategy.route = AsyncMock(
            return_value=RoutingDecision(
                query="Test",
                data_sources=[],
                strategy="test",
                confidence=0.3,
                reasoning="Low confidence",
            ),
        )

        high_confidence_strategy = AsyncMock()
        high_confidence_strategy.route = AsyncMock(
            return_value=RoutingDecision(
                query="Test",
                data_sources=[],
                strategy="test",
                confidence=0.9,
                reasoning="High confidence",
            ),
        )

        router = HybridRouter(
            strategies=[low_confidence_strategy, high_confidence_strategy],
            confidence_threshold=0.7,
            use_ensemble=False,
        )

        features = QueryFeatures(
            text="Test",
            length=4,
            intent=QueryIntent.FACTUAL,
        )

        decision = await router.route(features, [])

        # Should return high confidence decision
        assert decision.confidence == 0.9

    @pytest.mark.asyncio
    async def test_ensemble_routing(self):
        """Test ensemble routing (combine all)."""
        source1 = DataSourceProtocol(
            name="s1", type=DataSourceType.VECTOR_STORE, description="S1",
        )
        source2 = DataSourceProtocol(
            name="s2", type=DataSourceType.KEYWORD_INDEX, description="S2",
        )

        strategy1 = AsyncMock()
        strategy1.route = AsyncMock(
            return_value=RoutingDecision(
                query="Test",
                data_sources=[source1],
                strategy="dense",
                confidence=0.8,
                reasoning="Strategy 1",
            ),
        )

        strategy2 = AsyncMock()
        strategy2.route = AsyncMock(
            return_value=RoutingDecision(
                query="Test",
                data_sources=[source1],
                strategy="dense",
                confidence=0.9,
                reasoning="Strategy 2",
            ),
        )

        router = HybridRouter(
            strategies=[strategy1, strategy2],
            use_ensemble=True,
        )

        features = QueryFeatures(
            text="Test",
            length=4,
            intent=QueryIntent.FACTUAL,
        )

        decision = await router.route(features, [source1, source2])

        # Should combine decisions
        assert decision.metadata.get("ensemble") is True
        assert decision.confidence > 0.5  # Average of 0.8 and 0.9


class TestQueryRouter:
    """Test QueryRouter class."""

    @pytest.mark.asyncio
    async def test_create_router(self):
        """Test creating query router."""
        router = QueryRouter()
        assert router.analyzer is not None
        assert router.strategy is not None

    @pytest.mark.asyncio
    async def test_register_source(self):
        """Test registering data source."""
        router = QueryRouter()

        source = DataSourceProtocol(
            name="test",
            type=DataSourceType.VECTOR_STORE,
            description="Test",
        )

        router.register_source(source)
        assert len(router.data_sources) == 1
        assert router.data_sources[0] == source

    @pytest.mark.asyncio
    async def test_unregister_source(self):
        """Test unregistering data source."""
        router = QueryRouter()

        source = DataSourceProtocol(
            name="test",
            type=DataSourceType.VECTOR_STORE,
            description="Test",
        )

        router.register_source(source)
        assert router.unregister_source("test") is True
        assert router.unregister_source("nonexistent") is False

    @pytest.mark.asyncio
    async def test_get_source(self):
        """Test getting data source."""
        router = QueryRouter()

        source = DataSourceProtocol(
            name="test",
            type=DataSourceType.VECTOR_STORE,
            description="Test",
        )

        router.register_source(source)
        assert router.get_source("test") == source
        assert router.get_source("nonexistent") is None

    @pytest.mark.asyncio
    async def test_list_sources(self):
        """Test listing data sources."""
        router = QueryRouter()

        source1 = DataSourceProtocol(
            name="s1", type=DataSourceType.VECTOR_STORE, description="S1",
        )
        source2 = DataSourceProtocol(
            name="s2", type=DataSourceType.KEYWORD_INDEX, description="S2",
        )

        router.register_source(source1)
        router.register_source(source2)

        sources = router.list_sources()
        assert len(sources) == 2

    @pytest.mark.asyncio
    async def test_route_query(self):
        """Test routing a query."""
        router = QueryRouter()

        source = DataSourceProtocol(
            name="vec",
            type=DataSourceType.VECTOR_STORE,
            description="Vector store",
            priority=10,
        )

        router.register_source(source)

        decision = await router.route("What is Python?")

        assert decision.query == "What is Python?"
        assert len(decision.data_sources) > 0
        assert decision.confidence > 0

    @pytest.mark.asyncio
    async def test_route_batch(self):
        """Test routing multiple queries."""
        router = QueryRouter()

        source = DataSourceProtocol(
            name="vec",
            type=DataSourceType.VECTOR_STORE,
            description="Vector store",
        )

        router.register_source(source)

        queries = ["Query 1", "Query 2", "Query 3"]
        decisions = await router.route_batch(queries)

        assert len(decisions) == 3
        assert all(d.query in queries for d in decisions)

    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        """Test statistics tracking."""
        router = QueryRouter()

        source = DataSourceProtocol(
            name="vec",
            type=DataSourceType.VECTOR_STORE,
            description="Vector store",
        )

        router.register_source(source)

        # Route some queries
        await router.route("Query 1")
        await router.route("Query 2")
        await router.route("Query 3")

        stats = router.get_statistics()

        assert stats.total_queries == 3
        assert len(stats.by_strategy) > 0
        assert stats.avg_confidence > 0

    @pytest.mark.asyncio
    async def test_reset_statistics(self):
        """Test resetting statistics."""
        router = QueryRouter()

        source = DataSourceProtocol(
            name="vec",
            type=DataSourceType.VECTOR_STORE,
            description="Vector store",
        )

        router.register_source(source)

        await router.route("Query 1")
        router.reset_statistics()

        stats = router.get_statistics()
        assert stats.total_queries == 0

    @pytest.mark.asyncio
    async def test_set_strategy(self):
        """Test setting routing strategy."""
        router = QueryRouter()

        new_strategy = RuleBasedRouter()
        router.set_strategy(new_strategy)

        assert router.strategy == new_strategy

    @pytest.mark.asyncio
    async def test_set_analyzer(self):
        """Test setting query analyzer."""
        router = QueryRouter()

        new_analyzer = QueryAnalyzer(extract_keywords=False)
        router.set_analyzer(new_analyzer)

        assert router.analyzer == new_analyzer


class TestRoutingStatistics:
    """Test RoutingStatistics class."""

    def test_create_statistics(self):
        """Test creating statistics."""
        stats = RoutingStatistics()
        assert stats.total_queries == 0
        assert stats.avg_confidence == 0.0

    def test_update_statistics(self):
        """Test updating statistics."""
        stats = RoutingStatistics()

        source = DataSourceProtocol(
            name="test", type=DataSourceType.VECTOR_STORE, description="Test",
        )

        decision = RoutingDecision(
            query="Test",
            data_sources=[source],
            strategy="dense",
            confidence=0.9,
            reasoning="Test",
        )

        stats.update(decision)

        assert stats.total_queries == 1
        assert stats.by_strategy["dense"] == 1
        assert stats.by_data_source["test"] == 1
        assert stats.avg_confidence == 0.9
        assert stats.high_confidence_count == 1

    def test_to_dict(self):
        """Test converting statistics to dictionary."""
        stats = RoutingStatistics()
        stats.total_queries = 10
        stats.high_confidence_count = 7

        result = stats.to_dict()

        assert result["total_queries"] == 10
        assert result["high_confidence_count"] == 7
        assert result["high_confidence_rate"] == 0.7
