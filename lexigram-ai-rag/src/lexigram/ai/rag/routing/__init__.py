"""Query routing for RAG systems.

This module provides intelligent query routing to appropriate data sources,
indexes, and retrieval strategies based on query analysis.

Core components:
- QueryAnalyzer: Extract features from queries
- RoutingStrategy: Decision-making logic (rule-based, semantic, LLM, hybrid)
- QueryRouter: Main orchestrator for routing decisions
- DataSourceProtocol: Registry of available data sources

Example:
    ```python
    from lexigram.ai.rag import (
        QueryRouter,
        QueryAnalyzer,
        RuleBasedRouter,
        DataSourceProtocol,
        DataSourceType
    )

    # Register data sources
    router = QueryRouter()
    router.register_source(DataSourceProtocol(
        name="technical_docs",
        type=DataSourceType.VECTOR_STORE,
        description="Technical documentation vector store",
        capabilities=["dense_search", "semantic_search"]
    ))

    # Route query
    decision = await router.route("How do I configure authentication?")
    logger.info(f"Route to: {decision.data_sources[0].name}")
    logger.info(f"Strategy: {decision.strategy}")
    logger.info(f"Confidence: {decision.confidence}")
    ```
"""

from __future__ import annotations

from lexigram.ai.rag.routing.analyzer import QueryAnalyzer
from lexigram.ai.rag.routing.router import QueryRouter, RoutingStatistics

# Strategies
from lexigram.ai.rag.routing.strategies.base import RoutingStrategy
from lexigram.ai.rag.routing.strategies.hybrid import HybridRouter
from lexigram.ai.rag.routing.strategies.llm import LLMRouter
from lexigram.ai.rag.routing.strategies.rule_based import (
    RoutingRule,
    RuleBasedRouter,
)
from lexigram.ai.rag.routing.strategies.semantic import (
    RoutingPattern,
    SemanticRouter,
)
from lexigram.ai.rag.routing.types import (
    DataSource,
    DataSourceType,
    QueryFeatures,
    QueryIntent,
    RoutingDecision,
)

__all__ = [
    "DataSource",
    "DataSourceType",
    "HybridRouter",
    "LLMRouter",
    # Main components
    "QueryAnalyzer",
    "QueryFeatures",
    # Core types
    "QueryIntent",
    "QueryRouter",
    "RoutingDecision",
    "RoutingPattern",
    "RoutingRule",
    "RoutingStatistics",
    # Strategies
    "RoutingStrategy",
    "RuleBasedRouter",
    "SemanticRouter",
]
