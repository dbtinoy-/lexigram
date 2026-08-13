"""Tests for query routing module."""

from __future__ import annotations

from unittest.mock import AsyncMock
import pytest
from unittest.mock import AsyncMock

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
        assert decision.confidence > 0.5


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
