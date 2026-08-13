"""Cross-modal retrieval for multi-modal RAG.

This module enables querying across modalities:
- Text query → Find images
- Image query → Find text
- Text query → Find audio/video
- Mixed modality queries
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.data.vector.protocols import VectorStoreProtocol

from lexigram.ai.rag.multimodal.embeddings.multimodal import (
    MultiModalEmbedder,
)
from lexigram.ai.rag.multimodal.types import (
    AudioDocument,
    ImageDocument,
    Modality,
    MultiModalDocument,
    VideoDocument,
)


class CrossModalRetriever:
    """Retriever for cross-modal search.

    Enables searching across different modalities using aligned
    embedding spaces (e.g., CLIP for text-image).

    Args:
        embedder: MultiModalEmbedder instance
        vector_store: Vector store for similarity search
        default_top_k: Default number of results to return

    Example:
        >>> retriever = CrossModalRetriever(embedder, vector_store)
        >>> # Text to image search
        >>> images = await retriever.search_by_text(
        ...     query="a cat sitting on a mat",
        ...     target_modality=Modality.IMAGE,
        ...     top_k=10
        ... )
    """

    def __init__(
        self,
        embedder: MultiModalEmbedder,
        vector_store: VectorStoreProtocol | None = None,
        default_top_k: int = 10,
    ):
        """Initialize cross-modal retriever."""
        self.embedder = embedder
        self.vector_store = vector_store
        self.default_top_k = default_top_k

        # Document storage (simple in-memory for now)
        self._documents: dict[
            str,
            list[ImageDocument | AudioDocument | VideoDocument | MultiModalDocument],
        ] = {
            Modality.IMAGE.value: [],
            Modality.AUDIO.value: [],
            Modality.VIDEO.value: [],
            Modality.MULTIMODAL.value: [],
        }

        # Embedding cache
        self._embeddings: dict[str, list[list[float]]] = {
            Modality.IMAGE.value: [],
            Modality.AUDIO.value: [],
            Modality.VIDEO.value: [],
            Modality.MULTIMODAL.value: [],
        }

    async def index_image(self, image: ImageDocument) -> None:
        """Index an image document.

        Args:
            image: ImageDocument to index
        """
        # Embed image
        embedding = await self.embedder.embed_image(image)

        # Store document and embedding
        self._documents[Modality.IMAGE.value].append(image)
        self._embeddings[Modality.IMAGE.value].append(embedding)

        # Store embedding if available
        image.embedding = embedding

    async def index_audio(self, audio: AudioDocument) -> None:
        """Index an audio document.

        Args:
            audio: AudioDocument to index
        """
        # Embed audio
        embedding = await self.embedder.embed_audio(audio)

        # Store
        self._documents[Modality.AUDIO.value].append(audio)
        self._embeddings[Modality.AUDIO.value].append(embedding)

        audio.embedding = embedding

    async def index_video(self, video: VideoDocument) -> None:
        """Index a video document.

        Args:
            video: VideoDocument to index
        """
        # Embed video
        embedding = await self.embedder.embed_video(video)

        # Store
        self._documents[Modality.VIDEO.value].append(video)
        self._embeddings[Modality.VIDEO.value].append(embedding)

        video.embedding = embedding

    async def index_multimodal(self, document: MultiModalDocument) -> None:
        """Index a multi-modal document.

        Args:
            document: MultiModalDocument to index
        """
        # Embed document
        embeddings = await self.embedder.embed(document)

        # Store using fused embedding
        if embeddings.fused:
            self._documents[Modality.MULTIMODAL.value].append(document)
            self._embeddings[Modality.MULTIMODAL.value].append(embeddings.fused)

            document.embeddings = embeddings

    async def search_by_text(
        self,
        query: str,
        target_modality: Modality,
        top_k: int | None = None,
    ) -> list[ImageDocument | AudioDocument | VideoDocument | MultiModalDocument]:
        """Search for documents using text query.

        Args:
            query: Text query
            target_modality: Modality to search in
            top_k: Number of results to return

        Returns:
            List of documents ranked by similarity
        """
        top_k = top_k or self.default_top_k

        # Embed query text
        query_embedding = await self.embedder.embed_text(query)

        # Search in target modality
        return self._similarity_search(
            query_embedding,
            target_modality,
            top_k,
        )

    async def search_by_image(
        self,
        image: ImageDocument,
        target_modality: Modality,
        top_k: int | None = None,
    ) -> list[ImageDocument | AudioDocument | VideoDocument | MultiModalDocument]:
        """Search for documents using image query.

        Args:
            image: ImageDocument query
            target_modality: Modality to search in
            top_k: Number of results to return

        Returns:
            List of documents ranked by similarity
        """
        top_k = top_k or self.default_top_k

        # Embed query image
        query_embedding = await self.embedder.embed_image(image)

        # Search in target modality
        return self._similarity_search(
            query_embedding,
            target_modality,
            top_k,
        )

    async def search_by_embedding(
        self,
        embedding: list[float],
        target_modality: Modality,
        top_k: int | None = None,
    ) -> list[ImageDocument | AudioDocument | VideoDocument | MultiModalDocument]:
        """Search using a pre-computed embedding.

        Args:
            embedding: Query embedding vector
            target_modality: Modality to search in
            top_k: Number of results to return

        Returns:
            List of documents ranked by similarity
        """
        top_k = top_k or self.default_top_k

        return self._similarity_search(
            embedding,
            target_modality,
            top_k,
        )

    async def hybrid_search(
        self,
        text_query: str | None = None,
        image_query: ImageDocument | None = None,
        target_modality: Modality = Modality.MULTIMODAL,
        top_k: int | None = None,
        text_weight: float = 0.5,
    ) -> list[ImageDocument | AudioDocument | VideoDocument | MultiModalDocument]:
        """Perform hybrid search using multiple query modalities.

        Args:
            text_query: Optional text query
            image_query: Optional image query
            target_modality: Modality to search in
            top_k: Number of results to return
            text_weight: Weight for text query (0-1)

        Returns:
            List of documents ranked by combined similarity
        """
        import numpy as np

        top_k = top_k or self.default_top_k

        # Get embeddings
        embeddings = []
        weights = []

        if text_query:
            text_emb = await self.embedder.embed_text(text_query)
            embeddings.append(text_emb)
            weights.append(text_weight)

        if image_query:
            image_emb = await self.embedder.embed_image(image_query)
            embeddings.append(image_emb)
            weights.append(1.0 - text_weight)

        if not embeddings:
            return []

        # Combine embeddings (weighted average)
        np_weights = np.array(weights) / sum(weights)
        combined_embedding = np.average(embeddings, axis=0, weights=np_weights).tolist()

        # Search
        return self._similarity_search(
            combined_embedding,
            target_modality,
            top_k,
        )

    def _similarity_search(
        self,
        query_embedding: list[float],
        target_modality: Modality,
        top_k: int,
    ) -> list[ImageDocument | AudioDocument | VideoDocument | MultiModalDocument]:
        """Perform similarity search in target modality.

        Args:
            query_embedding: Query embedding vector
            target_modality: Modality to search in
            top_k: Number of results

        Returns:
            List of top-k documents
        """
        import numpy as np

        modality_key = target_modality.value

        # Get documents and embeddings
        documents = self._documents.get(modality_key, [])
        embeddings = self._embeddings.get(modality_key, [])

        if not documents:
            return []

        # Compute similarities
        similarities = []
        query_emb = np.array(query_embedding)

        for doc_emb in embeddings:
            doc_emb_np = np.array(doc_emb)

            # Cosine similarity
            similarity = np.dot(query_emb, doc_emb_np) / (
                np.linalg.norm(query_emb) * np.linalg.norm(doc_emb_np)
            )

            similarities.append(similarity)

        # Sort by similarity (descending)
        sorted_indices = np.argsort(similarities)[::-1]

        # Return top-k
        top_k = min(top_k, len(documents))
        return [documents[i] for i in sorted_indices[:top_k]]

    def get_statistics(self) -> dict[str, int]:
        """Get indexing statistics.

        Returns:
            Dictionary of modality -> document count
        """
        return {modality: len(docs) for modality, docs in self._documents.items()}

    def clear(self) -> None:
        """Clear all indexed documents."""
        for modality in self._documents:
            self._documents[modality] = []
            self._embeddings[modality] = []
