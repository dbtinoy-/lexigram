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
