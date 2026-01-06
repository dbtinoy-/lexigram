"""HyDE strategy registry for query generation strategies."""

from __future__ import annotations

from typing import Any, Protocol

from lexigram.ai.rag.hyde.generators import (
    MultipleHyDEGenerator,
    ReverseHyDEGenerator,
    SingleHyDEGenerator,
    WeightedHyDEGenerator,
)
from lexigram.ai.rag.hyde.types import HyDEStrategy
from lexigram.contracts.ai import EmbeddingClientProtocol, LLMClientProtocol


class HyDEStrategyHandler(Protocol):
    """Protocol for HyDE strategy handlers."""

    def can_handle(self, strategy: HyDEStrategy) -> bool:
        """Check if this handler can handle the strategy."""
        ...

    async def create_and_generate(
        self,
        strategy: HyDEStrategy,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol,
        query: str,
        num_documents: int,
        kwargs: dict[str, Any],
    ) -> Any:
        """Create generator and generate queries."""
        ...


class SingleHyDEStrategyHandler:
    """Handler for SINGLE HyDE strategy."""

    def can_handle(self, strategy: HyDEStrategy) -> bool:
        return strategy == HyDEStrategy.SINGLE

    async def create_and_generate(
        self,
        strategy: HyDEStrategy,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol,
        query: str,
        num_documents: int,
        kwargs: dict[str, Any],
    ) -> Any:
        generator = SingleHyDEGenerator(llm_client, embedding_client)
        return await generator.generate(query, num_documents=num_documents, **kwargs)


class MultipleHyDEStrategyHandler:
    """Handler for MULTIPLE HyDE strategy."""

    def can_handle(self, strategy: HyDEStrategy) -> bool:
        return strategy == HyDEStrategy.MULTIPLE

    async def create_and_generate(
        self,
        strategy: HyDEStrategy,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol,
        query: str,
        num_documents: int,
        kwargs: dict[str, Any],
    ) -> Any:
        generator = MultipleHyDEGenerator(llm_client, embedding_client)
        return await generator.generate(query, num_documents=num_documents, **kwargs)


class WeightedHyDEStrategyHandler:
    """Handler for WEIGHTED HyDE strategy."""

    def can_handle(self, strategy: HyDEStrategy) -> bool:
        return strategy == HyDEStrategy.WEIGHTED

    async def create_and_generate(
        self,
        strategy: HyDEStrategy,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol,
        query: str,
        num_documents: int,
        kwargs: dict[str, Any],
    ) -> Any:
        if not embedding_client:
            msg = "Weighted HyDE requires embedding_client"
            raise ValueError(msg)
        generator = WeightedHyDEGenerator(llm_client, embedding_client)
        return await generator.generate(query, num_documents=num_documents, **kwargs)


class ReverseHyDEStrategyHandler:
    """Handler for REVERSE HyDE strategy."""

    def can_handle(self, strategy: HyDEStrategy) -> bool:
        return strategy == HyDEStrategy.REVERSE

    async def create_and_generate(
        self,
        strategy: HyDEStrategy,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol,
        query: str,
        num_documents: int,
        kwargs: dict[str, Any],
    ) -> Any:
        generator = ReverseHyDEGenerator(llm_client, embedding_client)
        return await generator.generate(query, num_documents=num_documents, **kwargs)


class HyDEStrategyRegistry:
    """Central registry for HyDE strategy handlers."""

    def __init__(self) -> None:
        self._handlers: list[HyDEStrategyHandler] = []

    @classmethod
    def with_defaults(cls) -> HyDEStrategyRegistry:
        """Create a registry pre-populated with all built-in strategy handlers."""
        registry = cls()
        registry._handlers = [
            SingleHyDEStrategyHandler(),
            MultipleHyDEStrategyHandler(),
            WeightedHyDEStrategyHandler(),
            ReverseHyDEStrategyHandler(),
        ]
        return registry

    def register(self, handler: HyDEStrategyHandler) -> None:
        """Register a new strategy handler."""
        self._handlers.insert(0, handler)

    async def generate(
        self,
        strategy: HyDEStrategy,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol,
        query: str,
        num_documents: int,
        kwargs: dict[str, Any],
    ) -> Any:
        """Generate queries using the appropriate strategy."""
        for handler in self._handlers:
            if handler.can_handle(strategy):
                return await handler.create_and_generate(
                    strategy,
                    llm_client,
                    embedding_client,
                    query,
                    num_documents,
                    kwargs,
                )
        msg = f"Unknown HyDE strategy: {strategy}"
        raise ValueError(msg)
