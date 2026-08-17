"""Utility functions for HyDE."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.hyde.protocols import EmbeddingClientProtocol
from lexigram.ai.rag.hyde.types import HyDEResult, HyDEStrategy
from lexigram.contracts import (
    LLMClientProtocol,
)


# Convenience function
async def generate_hyde(
    query: str,
    llm_client: LLMClientProtocol,
    embedding_client: EmbeddingClientProtocol | None = None,
    strategy: HyDEStrategy = HyDEStrategy.SINGLE,
    num_documents: int | None = None,
    **kwargs: Any,
) -> HyDEResult:
    """Generate hypothetical documents for query.

    Args:
        query: User query
        llm_client: Client for generating hypothetical documents
        embedding_client: Optional client for generating embeddings
        strategy: HyDE strategy to use
        num_documents: Number of documents to generate
        **kwargs: Additional parameters

    Returns:
        HyDE result

    Raises:
        ValueError: If strategy is unknown or required client missing
    """
    from lexigram.ai.rag.hyde.strategy_registry import HyDEStrategyRegistry

    registry = HyDEStrategyRegistry.with_defaults()
    return await registry.generate(
        strategy,
        llm_client,
        embedding_client,  # type: ignore[arg-type]
        query,
        num_documents if num_documents is not None else 1,
        kwargs,
    )
