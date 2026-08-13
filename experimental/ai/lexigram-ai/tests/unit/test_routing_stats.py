"""Tests for query routing module."""

from __future__ import annotations

import pytest

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
