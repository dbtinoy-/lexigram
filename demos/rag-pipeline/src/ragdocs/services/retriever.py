"""Retriever built on Lexigram's vector collection protocol."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.data.vector import SearchQuery, VectorCollectionProtocol
from ragdocs.vector_store import DeterministicEmbedder


class Retriever:
    """Retrieve relevant chunks from one Lexigram vector collection."""

    def __init__(
        self,
        collection: VectorCollectionProtocol,
        embedder: DeterministicEmbedder,
        top_k: int = 5,
    ) -> None:
        self._collection = collection
        self._embedder = embedder
        self._top_k = top_k

    async def retrieve(
        self, query: str, top_k: int | None = None
    ) -> list[dict[str, Any]]:
        """Run a similarity search through the collection protocol."""
        search = SearchQuery(
            vector=self._embedder.embed(query),
            top_k=top_k or self._top_k,
            include_metadata=True,
        )
        results = await self._collection.search(search)
        return [
            {
                "id": result.id,
                "content": result.content or "",
                "metadata": result.metadata,
                "score": result.score,
            }
            for result in results
        ]

    async def retrieve_with_context(
        self, query: str, top_k: int | None = None
    ) -> dict[str, Any]:
        """Retrieve chunks and format them as LLM-ready context."""
        results = await self.retrieve(query, top_k)
        context = "\n\n".join(
            f"[{index}] {document['content']}"
            for index, document in enumerate(results, 1)
        )
        return {
            "query": query,
            "context": context,
            "sources": [
                {
                    "id": document["id"],
                    "score": document["score"],
                    "metadata": document["metadata"],
                }
                for document in results
            ],
        }

    async def get_stats(self) -> dict[str, Any]:
        """Return collection-level retrieval stats."""
        return {
            "collection": self._collection.name,
            "total_documents": await self._collection.count(),
            "top_k": self._top_k,
            "dimension": self._collection.dimension,
        }


__all__ = ["Retriever"]
