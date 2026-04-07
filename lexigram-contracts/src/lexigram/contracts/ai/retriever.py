"""Retriever contracts for Lexigram.

Defines retriever classes analogous to LangChain's.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseRetriever(ABC):
    """Base retriever (like LangChain's BaseRetriever).

    Retrieves relevant documents.
    """

    @abstractmethod
    def _get_relevant_documents(self, query: str) -> list[Any]:
        """Get relevant documents for a query.

        Args:
            query: The query string.

        Returns:
            List of relevant documents.
        """
        ...

    def get_relevant_documents(self, query: str) -> list[Any]:
        """Get relevant documents (sync version)."""
        return self._get_relevant_documents(query)

    def invoke(self, query: str) -> list[Any]:
        """Invoke the retriever (Runnable interface)."""
        return self.get_relevant_documents(query)

    async def aget_relevant_documents(self, query: str) -> list[Any]:
        """Get relevant documents (async version)."""
        return self._get_relevant_documents(query)

    async def ainvoke(self, query: str) -> list[Any]:
        """Invoke the retriever asynchronously."""
        return await self.aget_relevant_documents(query)


__all__ = [
    "BaseRetriever",
]
