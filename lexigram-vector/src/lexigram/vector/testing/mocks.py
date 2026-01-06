"""Mock vector store implementations for testing.

Provides in-memory vector storage without external dependencies.
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.vector import Document, RAGSearchResult
from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.result import Err, Ok, Result
from lexigram.vector.exceptions import VectorError as VectorStoreError

SearchResult = RAGSearchResult


class MockVectorStore:
    """Mock vector store for testing.

    Provides simple in-memory storage with simulated similarity search.
    Does not require actual embeddings - uses text similarity instead.

    Example:
        >>> store = MockVectorStore()
        >>> await store.add([
        ...     Document(text="Python is a programming language", id="1"),
        ...     Document(text="JavaScript is for web development", id="2")
        ... ])
        >>> results = await store.search(
        ...     query_vector=[],  # Ignored in mock
        ...     top_k=1
        ... )
    """

    def __init__(self, config: Any | None = None, **kwargs: Any):
        """Initialize mock vector store.

        Args:
            config: Optional vector store configuration
            **kwargs: Dependencies, including:
                - similarity_threshold: Minimum similarity score for results
                - dimension_size: Dimension size of embeddings to validate
        """
        self.config = config
        self.similarity_threshold = kwargs.get("similarity_threshold", 0.0)
        self.dimension_size = kwargs.get("dimension_size")
        self._documents: dict[str, Document] = {}
        self._closed = False

    async def add(
        self, documents: list[Document]
    ) -> Result[list[str], VectorStoreError]:
        """Add documents to store.

        Args:
            documents: Documents to add

        Returns:
            ``Ok(list[str])`` with document IDs on success.
        """
        import uuid

        ids = []
        for doc in documents:
            if self.dimension_size and doc.embedding is not None:
                if len(doc.embedding) != self.dimension_size:
                    return Err(
                        VectorStoreError(
                            f"Embedding dimension mismatch. Expected {self.dimension_size}, "
                            f"got {len(doc.embedding)}"
                        )
                    )

            doc_id = doc.id or str(uuid.uuid4())
            self._documents[doc_id] = Document(
                id=doc_id,
                text=doc.text,
                metadata=doc.metadata,
                embedding=doc.embedding,
            )
            ids.append(doc_id)

        return Ok(ids)

    async def batch_upsert(
        self,
        documents: list[Document],
        batch_size: int = 100,
    ) -> Result[int, VectorStoreError]:
        """Upsert documents in batches.

        Args:
            documents: List of documents to upsert.
            batch_size: Number of documents per batch. defaults to 100.

        Returns:
            ``Ok(int)`` with the total count of documents upserted, or
            ``Err(VectorStoreError)`` on failure.
        """
        # In the mock store, we can just process all of them directly
        # but to simulate batching, we chunk and process
        total = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            res = await self.add(batch)
            if res.is_err():
                return Err(res.unwrap_err())
            total += len(res.unwrap())

        return Ok(total)

    async def search(
        self,
        query_vector: list[float] | None = None,
        query: list[float] | str | None = None,
        k: int | None = None,
        top_k: int | None = None,
        filter: dict | None = None,
        filters: dict[str, Any] | None = None,
        filter_: dict | None = None,
        **kwargs: Any,
    ) -> Result[list[SearchResult], VectorStoreError]:
        """Search for similar documents.

        Uses simple text matching instead of vector similarity.
        This is sufficient for testing most RAG workflows.

        Args:
            query_vector: Query embedding (ignored in mock)
            k/top_k: Number of results
            filters/filter_: Metadata filters

        Returns:
            ``Ok(list[SearchResult])`` on success.
        """
        # Normalize args
        effective_filters = (
            filter
            or filters
            or filter_
            or kwargs.get("filter")
            or kwargs.get("filters")
            or kwargs.get("filter_")
        )

        # Filter by metadata if provided
        candidates = list(self._documents.values())

        if effective_filters:
            candidates = [
                doc
                for doc in candidates
                if doc.metadata
                and all(doc.metadata.get(k) == v for k, v in effective_filters.items())
            ]

        # Sort by document ID for deterministic results
        # In a real implementation, this would be by similarity score
        candidates.sort(key=lambda d: d.id or "")

        # Return top_k results
        results = []
        for i, doc in enumerate(
            candidates[: (k or top_k or kwargs.get("k") or kwargs.get("top_k") or 5)],
        ):
            # Simulate decreasing similarity scores
            score = 1.0 - (i * 0.1)
            if score < self.similarity_threshold:
                break

            results.append(
                SearchResult(
                    document=Document(
                        id=doc.id,
                        text=doc.text,
                        metadata=doc.metadata or {},
                    ),
                    score=score,
                    rank=i,
                ),
            )

        return Ok(results)

    async def delete(self, ids: list[str]) -> Result[int, VectorStoreError]:
        """Delete documents by ID.

        Args:
            ids: Document IDs to delete

        Returns:
            ``Ok(int)`` with the count of deleted documents.
        """
        count = 0
        for doc_id in ids:
            if self._documents.pop(doc_id, None) is not None:
                count += 1
        return Ok(count)

    def get_document_count(self) -> int:
        """Get total number of documents.

        Returns:
            Document count
        """
        return len(self._documents)

    def clear(self) -> None:
        """Clear all documents."""
        self._documents.clear()

    async def close(self) -> None:
        """Close store."""
        self._closed = True

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Perform health check.

        Returns:
            Structured health check result.
        """
        if self._closed:
            return HealthCheckResult(
                component="vector.mock",
                status=HealthStatus.UNHEALTHY,
                error="Store is closed",
                details={"provider": "mock"},
            )

        return HealthCheckResult(
            component="vector.mock",
            status=HealthStatus.HEALTHY,
            details={
                "provider": "mock",
                "document_count": len(self._documents),
            },
        )

    async def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
        collection_name: str | None = None,
    ) -> list[str]:
        """Convenience wrapper to add raw texts with optional embeddings/metadata.

        Raises:
            VectorStoreError: If adding documents fails (unwraps the Result).
        """
        documents = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            embedding = embeddings[i] if embeddings and i < len(embeddings) else None
            documents.append(
                Document(id=None, text=text, metadata=metadata, embedding=embedding),
            )
        result = await self.add(documents)
        if result.is_err():
            raise result.unwrap_err()
        return result.unwrap()

    async def __aenter__(self) -> MockVectorStore:  # noqa: PYI034
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    def __repr__(self) -> str:
        """String representation."""
        return f"MockVectorStore(documents={len(self._documents)})"


class MockVectorStoreWithSimilarity(MockVectorStore):
    """Mock vector store with actual similarity calculation.

    Uses cosine similarity on provided embeddings if available,
    falls back to text matching otherwise.

    Example:
        >>> store = MockVectorStoreWithSimilarity()
        >>> await store.add([
        ...     Document(
        ...         text="Python programming",
        ...         embedding=[0.1, 0.2, 0.3],
        ...         id="1"
        ...     )
        ... ])
        >>> results = await store.search(
        ...     query_vector=[0.1, 0.2, 0.3],
        ...     top_k=1
        ... )
        >>> results[0].score  # High similarity
        1.0
    """

    def _cosine_similarity(
        self,
        vec1: list[float],
        vec2: list[float],
    ) -> float:
        """Calculate cosine similarity between vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0-1)
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))

        # Magnitudes
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def search(
        self,
        query_vector: list[float] | None = None,
        query: list[float] | str | None = None,
        k: int | None = None,
        top_k: int | None = None,
        filter: dict | None = None,
        filters: dict[str, Any] | None = None,
        filter_: dict | None = None,
        **kwargs: Any,
    ) -> Result[list[SearchResult], VectorStoreError]:
        """Search with actual similarity calculation.

        Args:
            query_vector: Query embedding vector
            k/top_k: Number of results
            filters/filter_: Metadata filters

        Returns:
            ``Ok(list[SearchResult])`` sorted by similarity.
        """
        # Normalize args
        effective_filters = (
            filter
            or filters
            or filter_
            or kwargs.get("filter")
            or kwargs.get("filters")
            or kwargs.get("filter_")
        )

        # Filter by metadata
        candidates = list(self._documents.values())

        if effective_filters:
            candidates = [
                doc
                for doc in candidates
                if doc.metadata
                and all(doc.metadata.get(k) == v for k, v in effective_filters.items())
            ]

        # Calculate similarity scores
        scored_docs = []
        for doc in candidates:
            if doc.embedding and query_vector:
                # Use actual cosine similarity
                score = self._cosine_similarity(query_vector, doc.embedding)
            else:
                # Fall back to mock scoring
                score = 0.5

            if score >= self.similarity_threshold:
                scored_docs.append((doc, score))

        # Sort by score descending
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # Return top_k results
        results = []
        for rank, (doc, score) in enumerate(scored_docs[:top_k]):
            results.append(
                SearchResult(
                    document=Document(
                        id=doc.id or "",
                        text=doc.text,
                        metadata=doc.metadata or {},
                        embedding=doc.embedding,
                    ),
                    score=score,
                    rank=rank,
                ),
            )

        return Ok(results)


class MockVectorStoreWithErrors(MockVectorStore):
    """Mock vector store that can simulate errors.

    Useful for testing error handling.

    Example:
        >>> store = MockVectorStoreWithErrors(fail_on_search=True)
        >>> await store.search([0.1, 0.2], top_k=5)  # Returns Err(VectorStoreError)
    """

    def __init__(
        self,
        fail_on_add: bool = False,
        fail_on_search: bool = False,
        fail_on_delete: bool = False,
        error_rate: float | None = None,
        error_message: str = "Mock vector store error",
    ):
        """Initialize error-simulating mock.

        Args:
            fail_on_add: Whether to fail on add()
            fail_on_search: Whether to fail on search()
            fail_on_delete: Whether to fail on delete()
            error_rate: Probabilistic error rate (0-1), compatible with fixtures
            error_message: Error message to raise
        """
        super().__init__()
        self.fail_on_add = fail_on_add
        self.fail_on_search = fail_on_search
        self.fail_on_delete = fail_on_delete
        self.error_rate = error_rate
        self.error_message = error_message

    async def add(
        self, documents: list[Document]
    ) -> Result[list[str], VectorStoreError]:
        """Add with possible error."""
        if self.fail_on_add:
            return Err(VectorStoreError(self.error_message))
        return await super().add(documents)

    async def search(
        self,
        query_vector: list[float] | None = None,
        query: list[float] | str | None = None,
        k: int | None = None,
        top_k: int | None = None,
        filter: dict | None = None,
        filters: dict[str, Any] | None = None,
        filter_: dict | None = None,
        **kwargs: Any,
    ) -> Result[list[SearchResult], VectorStoreError]:
        """Search with possible error."""
        if self.fail_on_search:
            return Err(VectorStoreError(self.error_message))
        return await super().search(
            query_vector,
            k=k,
            top_k=top_k,
            filter=filter,
            filters=filters,
            filter_=filter_,
            **kwargs,
        )

    async def delete(self, ids: list[str]) -> Result[int, VectorStoreError]:
        """Delete with possible error."""
        if self.fail_on_delete:
            return Err(VectorStoreError(self.error_message))
        return await super().delete(ids)


__all__ = [
    "MockVectorStore",
    "MockVectorStoreWithErrors",
    "MockVectorStoreWithSimilarity",
]
