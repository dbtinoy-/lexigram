"""Reasoning strategy registry for multi-hop reasoning."""

from __future__ import annotations

from typing import Any, Protocol

from lexigram.ai.rag.reasoning.base import ReasoningStrategy
from lexigram.ai.rag.reasoning.chain_of_thought import ChainOfThoughtReasoner
from lexigram.ai.rag.reasoning.decomposition import QueryDecomposer
from lexigram.ai.rag.reasoning.iterative import IterativeRefinementReasoner
from lexigram.ai.rag.reasoning.multi_hop import MultiHopReasoner
from lexigram.contracts.ai import LLMClientProtocol
from lexigram.contracts.ai.vector import DocumentVectorStoreProtocol

VectorStoreProtocol = DocumentVectorStoreProtocol


class ReasoningStrategyHandler(Protocol):
    """Protocol for reasoning strategy handlers."""

    def can_handle(self, strategy: ReasoningStrategy) -> bool:
        """Check if this handler can handle the strategy."""
        ...

    async def create_and_reason(
        self,
        strategy: ReasoningStrategy,
        llm_client: LLMClientProtocol,
        vector_store: VectorStoreProtocol,
        query: str,
        kwargs: dict[str, Any],
    ) -> Any:
        """Create reasoner and execute reasoning."""
        ...


class MultiHopReasoningHandler:
    """Handler for MULTI_HOP reasoning strategy."""

    def can_handle(self, strategy: ReasoningStrategy) -> bool:
        return strategy == ReasoningStrategy.MULTI_HOP

    async def create_and_reason(
        self,
        strategy: ReasoningStrategy,
        llm_client: LLMClientProtocol,
        vector_store: VectorStoreProtocol,
        query: str,
        kwargs: dict[str, Any],
    ) -> Any:
        reasoner = MultiHopReasoner(llm_client, vector_store, **kwargs)  # type: ignore[arg-type]
        return await reasoner.reason(query, **kwargs)


class ChainOfThoughtReasoningHandler:
    """Handler for CHAIN_OF_THOUGHT reasoning strategy."""

    def can_handle(self, strategy: ReasoningStrategy) -> bool:
        return strategy == ReasoningStrategy.CHAIN_OF_THOUGHT

    async def create_and_reason(
        self,
        strategy: ReasoningStrategy,
        llm_client: LLMClientProtocol,
        vector_store: VectorStoreProtocol,
        query: str,
        kwargs: dict[str, Any],
    ) -> Any:
        reasoner = ChainOfThoughtReasoner(llm_client, **kwargs)
        return await reasoner.reason(query, **kwargs)


class DecompositionReasoningHandler:
    """Handler for DECOMPOSITION reasoning strategy."""

    def can_handle(self, strategy: ReasoningStrategy) -> bool:
        return strategy == ReasoningStrategy.DECOMPOSITION

    async def create_and_reason(
        self,
        strategy: ReasoningStrategy,
        llm_client: LLMClientProtocol,
        vector_store: VectorStoreProtocol,
        query: str,
        kwargs: dict[str, Any],
    ) -> Any:
        reasoner = QueryDecomposer(llm_client, vector_store, **kwargs)  # type: ignore[arg-type]
        return await reasoner.reason(query, **kwargs)


class IterativeRefinementReasoningHandler:
    """Handler for ITERATIVE_REFINEMENT reasoning strategy."""

    def can_handle(self, strategy: ReasoningStrategy) -> bool:
        return strategy == ReasoningStrategy.ITERATIVE_REFINEMENT

    async def create_and_reason(
        self,
        strategy: ReasoningStrategy,
        llm_client: LLMClientProtocol,
        vector_store: VectorStoreProtocol,
        query: str,
        kwargs: dict[str, Any],
    ) -> Any:
        reasoner = IterativeRefinementReasoner(llm_client, vector_store, **kwargs)  # type: ignore[arg-type]
        return await reasoner.reason(query, **kwargs)


class ReasoningStrategyRegistry:
    """Central registry for reasoning strategy handlers."""

    def __init__(self) -> None:
        self._handlers: list[ReasoningStrategyHandler] = []

    @classmethod
    def with_defaults(cls) -> ReasoningStrategyRegistry:
        """Create a registry pre-populated with all built-in strategy handlers."""
        registry = cls()
        registry._handlers = [
            MultiHopReasoningHandler(),
            ChainOfThoughtReasoningHandler(),
            DecompositionReasoningHandler(),
            IterativeRefinementReasoningHandler(),
        ]
        return registry

    def register(self, handler: ReasoningStrategyHandler) -> None:
        """Register a new strategy handler."""
        self._handlers.insert(0, handler)

    async def reason(
        self,
        strategy: ReasoningStrategy,
        llm_client: LLMClientProtocol,
        vector_store: VectorStoreProtocol,
        query: str,
        kwargs: dict[str, Any],
    ) -> Any:
        """Execute reasoning using the appropriate strategy."""
        for handler in self._handlers:
            if handler.can_handle(strategy):
                return await handler.create_and_reason(
                    strategy,
                    llm_client,
                    vector_store,
                    query,
                    kwargs,
                )
        msg = f"Unknown reasoning strategy: {strategy}"
        raise ValueError(msg)
