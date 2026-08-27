"""Retriever — retrieves relevant documents for queries."""

from __future__ import annotations

from typing import Any


class Retriever:
    """Retrieves relevant documents for queries.

    Demonstrates retrieval patterns for RAG pipelines.
    """

    def __init__(self, vector_store: Any, top_k: int = 5) -> None:
        self._vector_store = vector_store
        self._top_k = top_k

    async def retrieve(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        """Retrieve relevant documents for a query."""
        k = top_k or self._top_k
        return await self._vector_store.search(query, top_k=k)

    async def retrieve_with_context(self, query: str, top_k: int | None = None) -> dict[str, Any]:
        """Retrieve documents and format them as context."""
        results = await self.retrieve(query, top_k)

        context_parts = []
        for i, doc in enumerate(results, 1):
            context_parts.append(f"[{i}] {doc['content']}")

        return {
            "query": query,
            "context": "\n\n".join(context_parts),
            "sources": [
                {"id": doc["id"], "score": doc["score"], "metadata": doc["metadata"]}
                for doc in results
            ],
        }

    async def get_stats(self) -> dict[str, Any]:
        """Get retriever statistics."""
        count = await self._vector_store.count()
        return {
            "total_documents": count,
            "top_k": self._top_k,
        }
