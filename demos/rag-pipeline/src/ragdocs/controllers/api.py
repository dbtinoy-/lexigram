"""HTTP surface for the single-purpose RAG retrieval demo."""

from __future__ import annotations

import hashlib
from typing import Any

from lexigram.contracts.data.vector import VectorCollectionProtocol
from lexigram.web import Controller, get, post
from ragdocs.vector_store import DeterministicEmbedder


class RagApiController(Controller):
    """Expose chunk, upsert, search, and context-building controls."""

    prefix = "/api/rag"

    def __init__(
        self,
        collection: VectorCollectionProtocol | None = None,
        chunker: object = None,
        embedder: DeterministicEmbedder | None = None,
        retriever: object = None,
    ) -> None:
        self._collection = collection
        self._chunker = chunker
        self._embedder = embedder
        self._retriever = retriever

    @post("/ingest")
    async def ingest(self, body: dict[str, Any]) -> dict[str, Any]:
        """Chunk a document and upsert its embeddings into the collection."""
        content = body.get("content", "")
        if not content:
            return {"error": "Content is required"}

        metadata = body.get("metadata", {})
        chunks = self._chunker.chunk(content, metadata)
        texts = [chunk["content"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        embeddings = [self._embedder.embed(text) for text in texts]
        document_ids = [
            hashlib.sha256(f"{index}:{text}".encode()).hexdigest()[:16]
            for index, text in enumerate(texts)
        ]
        result = await self._collection.add_texts(
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=document_ids,
        )

        return {
            "chunks_stored": result.upserted_count,
            "document_ids": document_ids,
            "collection": self._collection.name,
        }

    @post("/search")
    async def search(self, body: dict[str, Any]) -> dict[str, Any]:
        """Search the Lexigram collection for similar chunks."""
        query = body.get("query", "")
        if not query:
            return {"error": "Query is required"}

        top_k = body.get("top_k", 5)
        results = await self._retriever.retrieve(query, top_k=top_k)
        return {"query": query, "results": results, "count": len(results)}

    @post("/search/context")
    async def search_context(self, body: dict[str, Any]) -> dict[str, Any]:
        """Search and return source-labelled context for an LLM prompt."""
        query = body.get("query", "")
        if not query:
            return {"error": "Query is required"}
        return await self._retriever.retrieve_with_context(
            query,
            top_k=body.get("top_k", 5),
        )

    @get("/stats")
    async def stats(self) -> dict[str, Any]:
        """Return collection and retriever stats."""
        return await self._retriever.get_stats()

    @get("/health")
    async def health(self) -> dict[str, Any]:
        """Report the demo pipeline health and active collection."""
        return {
            "status": "ok",
            "service": "ragdocs",
            "collection": self._collection.name,
        }


__all__ = ["RagApiController"]
