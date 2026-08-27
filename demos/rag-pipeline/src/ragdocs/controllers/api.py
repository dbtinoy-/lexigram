"""RAG API — HTTP surface for RAG pipeline operations.

Controllers are thin: they validate input, call a service, and
return a response dict.  No business logic lives here.
"""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get, post


class RagApiController(Controller):
    """HTTP surface for RAG pipeline operations.

    Delegates to services for business logic.  Returns dicts that
    the framework serialises to JSON.
    """

    prefix = "/api/rag"

    def __init__(
        self,
        vector_store: object = None,
        chunker: object = None,
        retriever: object = None,
    ) -> None:
        self._vector_store = vector_store
        self._chunker = chunker
        self._retriever = retriever

    @post("/ingest")
    async def ingest(self, body: dict[str, Any]) -> dict[str, Any]:
        """Ingest a document into the vector store.

        Body: ``{"content": "...", "metadata": {"source": "api"}}``
        """
        content = body.get("content", "")
        if not content:
            return {"error": "Content is required"}

        metadata = body.get("metadata", {})

        # Chunk the document
        chunks = self._chunker.chunk(content, metadata)

        # Store each chunk
        stored = []
        for chunk in chunks:
            doc = await self._vector_store.add(chunk["content"], chunk["metadata"])
            stored.append(doc.id)

        return {"chunks_stored": len(stored), "document_ids": stored}

    @post("/search")
    async def search(self, body: dict[str, Any]) -> dict[str, Any]:
        """Search for similar documents.

        Body: ``{"query": "...", "top_k": 5}``
        """
        query = body.get("query", "")
        if not query:
            return {"error": "Query is required"}

        top_k = body.get("top_k", 5)
        results = await self._retriever.retrieve(query, top_k=top_k)
        return {"query": query, "results": results, "count": len(results)}

    @post("/search/context")
    async def search_context(self, body: dict[str, Any]) -> dict[str, Any]:
        """Search and return formatted context.

        Body: ``{"query": "...", "top_k": 5}``
        """
        query = body.get("query", "")
        if not query:
            return {"error": "Query is required"}

        top_k = body.get("top_k", 5)
        return await self._retriever.retrieve_with_context(query, top_k=top_k)

    @get("/stats")
    async def stats(self) -> dict[str, Any]:
        """Get RAG pipeline statistics."""
        return await self._retriever.get_stats()

    @get("/health")
    async def health(self) -> dict[str, Any]:
        """Health check endpoint."""
        return {"status": "ok", "service": "ragdocs"}


__all__ = ["RagApiController"]
