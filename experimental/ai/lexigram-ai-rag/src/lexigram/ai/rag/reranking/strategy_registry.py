"""Reranking strategy registry for RAG document reordering.

Handler-based registry that stores handler instances and dispatches
to them based on strategy name via can_handle().
"""

from __future__ import annotations


class RerankingStrategyRegistry:
    """Registry of reranking strategy handlers.

    Reranking strategies reorder documents after initial retrieval
    using cross-encoders, LLM-based scoring, or fusion techniques.

    Uses a handler-based dispatch pattern where handlers implement
    can_handle(strategy: str) and create_and_rerank() methods.

    Usage::

        registry = RerankingStrategyRegistry()
        registry.register(FlashRankStrategyHandler())
        handler = registry.get("flashrank")
        result = await handler.create_and_rerank(strategy="flashrank", ...)
    """

    def __init__(self) -> None:
        """Initialize an empty handler registry."""
        self._handlers: list = []

    def register(self, handler: object) -> None:
        """Register a handler instance.

        Args:
            handler: A handler instance with can_handle(strategy) method.
        """
        self._handlers.append(handler)

    def get(self, strategy: str) -> object | None:
        """Get a handler that can handle the given strategy.

        Args:
            strategy: Strategy name to look up.

        Returns:
            First handler where can_handle(strategy) is True, or None.
        """
        for handler in self._handlers:
            if handler.can_handle(strategy):
                return handler
        return None


__all__ = ["RerankingStrategyRegistry"]
