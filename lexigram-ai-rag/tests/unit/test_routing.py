"""Unit tests for lexigram-ai-rag routing."""

from __future__ import annotations

import pytest

from lexigram.ai.rag.routing.analyzer import QueryAnalyzer
from lexigram.ai.rag.routing.router import QueryRouter, RoutingStatistics
from lexigram.ai.rag.routing.types import DataSource, DataSourceType, QueryIntent
from lexigram.ai.rag.routing.strategies.rule_based import RuleBasedRouter


class TestQueryAnalyzer:
    """Tests for QueryAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyze_factual_query(self) -> None:
        """Test analyzing a factual query."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("What is Python?")

        assert features.intent == QueryIntent.FACTUAL
        assert features.language == "en"

    @pytest.mark.asyncio
    async def test_analyze_procedural_query(self) -> None:
        """Test analyzing a procedural query."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("How do I configure authentication?")

        assert features.intent == QueryIntent.PROCEDURAL

    @pytest.mark.asyncio
    async def test_analyze_analytical_query(self) -> None:
        """Test analyzing an analytical query."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("Compare Python and JavaScript")

        assert features.intent == QueryIntent.ANALYTICAL

    @pytest.mark.asyncio
    async def test_analyze_creative_query(self) -> None:
        """Test analyzing a creative query."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("Write a poem about coding")

        assert features.intent == QueryIntent.CREATIVE

    @pytest.mark.asyncio
    async def test_analyze_navigational_query(self) -> None:
        """Test analyzing a navigational query."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("Find the documentation page")

        assert features.intent == QueryIntent.NAVIGATIONAL

    @pytest.mark.asyncio
    async def test_analyze_conversational_query(self) -> None:
        """Test analyzing a conversational query."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("Hello, how are you?")

        assert features.intent == QueryIntent.CONVERSATIONAL

    @pytest.mark.asyncio
    async def test_extract_keywords(self) -> None:
        """Test keyword extraction."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("Python programming language")

        assert "python" in features.keywords
        assert "programming" in features.keywords
        assert "language" in features.keywords

    @pytest.mark.asyncio
    async def test_detect_entities(self) -> None:
        """Test entity detection."""
        analyzer = QueryAnalyzer()
        features = await analyzer.analyze("What is Lexigram?")

        assert features.has_entities is True

    @pytest.mark.asyncio
    async def test_calculate_complexity(self) -> None:
        """Test complexity calculation."""
        analyzer = QueryAnalyzer()

        # Simple query
        simple_features = await analyzer.analyze("What is it?")
        assert simple_features.complexity < 0.5

        # Complex query
        complex_features = await analyzer.analyze(
            "How do I configure authentication, authorization, and permissions for the API?"
        )
        assert complex_features.complexity >= 0.3


class TestRoutingStatistics:
    """Tests for RoutingStatistics."""

    def test_statistics_initialization(self) -> None:
        """Test statistics initialization."""
        stats = RoutingStatistics()

        assert stats.total_queries == 0
        assert stats.avg_confidence == 0.0
        assert stats.high_confidence_count == 0
        assert stats.low_confidence_count == 0

    def test_statistics_update(self) -> None:
        """Test updating statistics."""
        from lexigram.ai.rag.routing.types import RoutingDecision

        stats = RoutingStatistics()
        decision = RoutingDecision(
            query="test query",
            data_sources=[],
            strategy="test",
            confidence=0.8,
            reasoning="test reasoning",
        )

        stats.update(decision)

        assert stats.total_queries == 1
        assert stats.avg_confidence == 0.8
        assert stats.high_confidence_count == 1

    def test_statistics_to_dict(self) -> None:
        """Test converting statistics to dictionary."""
        stats = RoutingStatistics()
        stats.total_queries = 10

        result = stats.to_dict()

        assert "total_queries" in result
        assert result["total_queries"] == 10


class TestQueryRouter:
    """Tests for QueryRouter."""

    @pytest.mark.asyncio
    async def test_router_initialization(self) -> None:
        """Test router initialization."""
        router = QueryRouter()

        assert router.analyzer is not None
        assert router.strategy is not None
        assert len(router.data_sources) == 0

    def test_register_source(self) -> None:
        """Test registering a data source."""
        router = QueryRouter()
        source = DataSource(
            name="test_source",
            type=DataSourceType.VECTOR_STORE,
            description="Test source",
            capabilities=["search"],
            priority=10,
        )

        router.register_source(source)

        assert len(router.data_sources) == 1
        assert router.data_sources[0].name == "test_source"

    def test_register_duplicate_source(self) -> None:
        """Test registering duplicate source updates."""
        router = QueryRouter()
        source1 = DataSource(
            name="test_source",
            type=DataSourceType.VECTOR_STORE,
            description="Source 1",
            capabilities=["search"],
            priority=10,
        )
        source2 = DataSource(
            name="test_source",
            type=DataSourceType.VECTOR_STORE,
            description="Source 2",
            capabilities=["search"],
            priority=20,
        )

        router.register_source(source1)
        router.register_source(source2)

        assert len(router.data_sources) == 1
        assert router.data_sources[0].description == "Source 2"

    def test_unregister_source(self) -> None:
        """Test unregistering a data source."""
        router = QueryRouter()
        source = DataSource(
            name="test_source",
            type=DataSourceType.VECTOR_STORE,
            description="Test source",
            capabilities=["search"],
            priority=10,
        )

        router.register_source(source)
        result = router.unregister_source("test_source")

        assert result is True
        assert len(router.data_sources) == 0

    def test_get_source(self) -> None:
        """Test getting a data source."""
        router = QueryRouter()
        source = DataSource(
            name="test_source",
            type=DataSourceType.VECTOR_STORE,
            description="Test source",
            capabilities=["search"],
            priority=10,
        )

        router.register_source(source)
        retrieved = router.get_source("test_source")

        assert retrieved is not None
        assert retrieved.name == "test_source"

    def test_list_sources(self) -> None:
        """Test listing all sources."""
        router = QueryRouter()
        router.register_source(DataSource(
            name="source1",
            type=DataSourceType.VECTOR_STORE,
            description="Source 1",
            capabilities=["search"],
            priority=10,
        ))
        router.register_source(DataSource(
            name="source2",
            type=DataSourceType.SQL_DATABASE,
            description="Source 2",
            capabilities=["query"],
            priority=5,
        ))

        sources = router.list_sources()

        assert len(sources) == 2

    def test_set_strategy(self) -> None:
        """Test setting a new strategy."""
        router = QueryRouter()
        new_strategy = RuleBasedRouter()

        router.set_strategy(new_strategy)

        assert router.strategy is new_strategy

    def test_reset_statistics(self) -> None:
        """Test resetting statistics."""
        router = QueryRouter()
        router.statistics.total_queries = 10

        router.reset_statistics()

        assert router.statistics.total_queries == 0


class TestQueryRouterRouting:
    """Tests for QueryRouter routing functionality."""

    @pytest.mark.asyncio
    async def test_route_simple_query(self) -> None:
        """Test routing a simple query."""
        router = QueryRouter()
        router.register_source(DataSource(
            name="docs",
            type=DataSourceType.VECTOR_STORE,
            description="Documentation",
            capabilities=["search"],
            priority=10,
        ))

        decision = await router.route("What is Python?")

        assert decision.strategy is not None
        assert decision.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_route_with_features(self) -> None:
        """Test routing with pre-extracted features."""
        router = QueryRouter()
        router.register_source(DataSource(
            name="docs",
            type=DataSourceType.VECTOR_STORE,
            description="Documentation",
            capabilities=["search"],
            priority=10,
        ))

        features = await router.analyzer.analyze("How do I configure API?")
        decision = await router.route("ignored", features=features)

        assert decision.strategy is not None

    @pytest.mark.asyncio
    async def test_route_batch(self) -> None:
        """Test routing multiple queries."""
        router = QueryRouter()
        router.register_source(DataSource(
            name="docs",
            type=DataSourceType.VECTOR_STORE,
            description="Documentation",
            capabilities=["search"],
            priority=10,
        ))

        queries = [
            "What is Python?",
            "How do I configure API?",
            "Compare Python and JavaScript",
        ]

        decisions = await router.route_batch(queries)

        assert len(decisions) == 3

    @pytest.mark.asyncio
    async def test_statistics_update_on_route(self) -> None:
        """Test statistics update after routing."""
        router = QueryRouter()
        router.register_source(DataSource(
            name="docs",
            type=DataSourceType.VECTOR_STORE,
            description="Documentation",
            capabilities=["search"],
            priority=10,
        ))

        await router.route("What is Python?")

        stats = router.get_statistics()
        assert stats.total_queries == 1
