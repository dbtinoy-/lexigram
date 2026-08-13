"""VectorStoreIndex - Index implementation using vector store."""

from __future__ import annotations

from lexigram.contracts.ai import ChunkerProtocol
from lexigram.contracts.ai.index import IndexError as IndexOpError
from lexigram.contracts.ai.llm import EmbeddingClientProtocol
from lexigram.contracts.ai.vector import (
    Document,
    DocumentVectorStoreProtocol,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class VectorStoreIndex:
    """Index implementation using vector store with chunking and embeddings.

    Composes chunking, embeddings, and vector store to provide a complete
    indexing solution for RAG applications.

    Example:
        >>> index = VectorStoreIndex(
        ...     vector_store=vector_store,
        ...     chunker=chunker,
        ...     embedding_client=embedding_client,
        ... )
        >>> doc = Document(text="Sample document text")
        >>> result = await index.insert([doc])
    """

    def __init__(
        self,
        vector_store: DocumentVectorStoreProtocol,
        chunker: ChunkerProtocol,
        embedding_client: EmbeddingClientProtocol,
    ) -> None:
        """Initialize VectorStoreIndex.

        Args:
            vector_store: The document vector store for storage and search.
            chunker: The chunker to split documents into smaller pieces.
            embedding_client: The embedding client for generating embeddings.
        """
        self._vector_store = vector_store
        self._chunker = chunker
        self._embedding_client = embedding_client

    async def insert(self, documents: list[Document]) -> list[str] | IndexOpError:
        """Insert documents into the index.

        Chunks the documents, generates embeddings, and stores in the vector store.

        Args:
            documents: List of documents to insert.

        Returns:
            Ok(list of document IDs) on success.
            Err(IndexOpError) on failure.
        """
        try:
            all_chunks: list[Document] = []
            for doc in documents:
                chunks = self._chunker.chunk(doc.text, doc.metadata)
                for chunk in chunks:
                    chunk_doc = Document(
                        text=chunk.text if hasattr(chunk, "text") else str(chunk),
                        metadata={**doc.metadata, **getattr(chunk, "metadata", {})},
                    )
                    all_chunks.append(chunk_doc)

            if not all_chunks:
                return []

            embedding_result = await self._embedding_client.embed(
                [doc.text for doc in all_chunks]
            )

            for doc, embedding in zip(all_chunks, embedding_result, strict=True):
                object.__setattr__(doc, "embedding", embedding)

            result = await self._vector_store.add(all_chunks)  # type: ignore[arg-type]
            if result.is_err():
                return IndexOpError(f"Failed to add documents: {result.unwrap_err()}")

            return result.unwrap()

        except Exception as e:
            logger.error("index_insert_failed", error=str(e))
            return IndexOpError(f"Failed to insert documents: {e}")

    async def delete(self, ids: list[str]) -> int | IndexOpError:
        """Delete documents by ID.

        Args:
            ids: List of document IDs to delete.

        Returns:
            Ok(count of deleted documents) on success.
            Err(IndexOpError) on failure.
        """
        try:
            result = await self._vector_store.delete(ids)
            if result.is_err():
                return IndexOpError(
                    f"Failed to delete documents: {result.unwrap_err()}"
                )
            return result.unwrap()
        except Exception as e:
            logger.error("index_delete_failed", error=str(e))
            return IndexOpError(f"Failed to delete documents: {e}")


__all__ = ["VectorStoreIndex"]
