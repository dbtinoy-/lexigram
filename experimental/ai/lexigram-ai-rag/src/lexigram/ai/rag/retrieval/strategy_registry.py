"""Retrieval strategy registry for RAG document ranking.

Maps strategy names to
:class:`~lexigram.contracts.ai.protocols.RetrievalStrategyProtocol`
implementations and instantiates on demand via
:meth:`~lexigram.primitives.registry.StrategyRegistry.instantiate`.
"""

from __future__ import annotations

from lexigram.logging import (
    get_logger,
)
from lexigram.primitives.registry import StrategyRegistry

logger = get_logger(__name__)


class RetrievalStrategyRegistry(StrategyRegistry):
    """Registry of retrieval strategy implementations.

    Strategies take a query and a set of candidate documents and return
    an ordered subset ranked by relevance.

    Usage::

        registry = RetrievalStrategyRegistry.with_defaults()
        strategy = registry.instantiate("mmr", lambda_param=0.7)
        results = await strategy.retrieve(query, candidates, top_k=5)
    """

    def __init__(self) -> None:
        super().__init__(name="retrieval.strategies", allow_overwrite=True)

    @classmethod
    def default_strategies(cls) -> dict[str, type]:
        """Declare the built-in retrieval strategies.

        Returns:
            Mapping of strategy key → class: ``"vector"`` and ``"mmr"``.
        """
        from lexigram.ai.rag.retrieval.strategies.mmr import MMRRetrievalStrategy
        from lexigram.ai.rag.retrieval.strategies.vector import VectorRetrievalStrategy

        return {
            "vector": VectorRetrievalStrategy,
            "mmr": MMRRetrievalStrategy,
        }


__all__ = ["RetrievalStrategyRegistry"]
