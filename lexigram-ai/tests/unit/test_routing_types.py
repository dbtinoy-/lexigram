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
