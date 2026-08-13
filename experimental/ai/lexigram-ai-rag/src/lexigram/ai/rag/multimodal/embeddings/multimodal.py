"""Multi-modal embedder combining different modalities.

This module provides a unified interface for embedding documents across
multiple modalities (text, image, audio, video) and fusing them into
combined representations.
"""

from __future__ import annotations

from typing import cast

import numpy as np

from lexigram.ai.rag.multimodal.embeddings.clip import CLIPEmbedding
from lexigram.ai.rag.multimodal.types import (
    AudioDocument,
    ImageDocument,
    Modality,
    MultiModalDocument,
    MultiModalEmbedding,
    VideoDocument,
)


class MultiModalEmbedder:
    """Embedder for multi-modal documents.

    Combines embeddings from different modalities and provides fusion strategies
    to create unified representations.

    Args:
        use_clip: Whether to use CLIP for image/text embeddings
        clip_model: CLIP model name
        fusion_method: Method for fusing embeddings ("concat", "average", "weighted")
        weights: Optional weights for weighted fusion

    Example:
        >>> embedder = MultiModalEmbedder()
        >>> # Embed multi-modal document
        >>> embeddings = await embedder.embed(multimodal_doc)
        >>> print(embeddings.available_modalities)
        [Modality.TEXT, Modality.IMAGE]
    """

    def __init__(
        self,
        use_clip: bool = True,
        clip_model: str = "openai/clip-vit-base-patch32",
        fusion_method: str = "concat",
        weights: dict[str, float] | None = None,
    ):
        """Initialize multi-modal embedder."""
        self.use_clip = use_clip
        self.fusion_method = fusion_method
        self.weights = weights or {
            "text": 1.0,
            "image": 1.0,
            "audio": 1.0,
            "video": 1.0,
        }

        # Initialize CLIP if requested
        self._clip: CLIPEmbedding | None = None
        if use_clip:
            self._clip = CLIPEmbedding(model_name=clip_model)

    async def embed_text(self, text: str) -> list[float]:
        """Embed text content.

        Args:
            text: Text to embed

        Returns:
            Text embedding vector
        """
        if self._clip:
            return cast("list[float]", await self._clip.embed_text(text))
        # Fallback: use simple text embedder
        msg = "Text embedding requires CLIP or custom embedder"
        raise NotImplementedError(msg)

    async def embed_image(self, image: ImageDocument) -> list[float]:
        """Embed image document.

        Args:
            image: ImageDocument to embed

        Returns:
            Image embedding vector
        """
        if self._clip:
            return cast("list[float]", await self._clip.embed_image(image))
        msg = "Image embedding requires CLIP or custom embedder"
        raise NotImplementedError(msg)

    async def embed_audio(self, audio: AudioDocument) -> list[float]:
        """Embed audio document.

        For now, uses transcript-based embedding if available.

        Args:
            audio: AudioDocument to embed

        Returns:
            Audio embedding vector
        """
        # Strategy: Use transcript if available, otherwise placeholder
        if audio.transcript and self._clip:
            return cast("list[float]", await self._clip.embed_text(audio.transcript))
        # Placeholder: could use Wav2Vec or other audio embedder
        msg = "Direct audio embedding not yet implemented. Enable transcription or provide transcript."
        raise NotImplementedError(msg)

    async def embed_video(self, video: VideoDocument) -> list[float]:
        """Embed video document.

        Combines frame embeddings and audio embedding.

        Args:
            video: VideoDocument to embed

        Returns:
            Video embedding vector
        """
        embeddings = []

        # Embed frames
        if video.frames and self._clip:
            frame_embeddings = []
            for frame in video.frames:
                frame_emb = await self._clip.embed_image(frame)
                frame_embeddings.append(frame_emb)

            # Average frame embeddings
            if frame_embeddings:
                avg_frame_emb = np.mean(frame_embeddings, axis=0).tolist()
                embeddings.append(avg_frame_emb)

        # Embed audio/transcript
        if video.transcript and self._clip:
            audio_emb = await self._clip.embed_text(video.transcript)
            embeddings.append(audio_emb)
        elif video.audio_track:
            try:
                audio_emb = await self.embed_audio(video.audio_track)
                embeddings.append(audio_emb)
            except NotImplementedError:
                pass

        # Fuse embeddings
        if not embeddings:
            msg = "No embeddings available to fuse"
            raise ValueError(msg)

        if len(embeddings) == 1:
            return embeddings[0]
        return self._fuse_embeddings(embeddings)

    async def embed(self, document: MultiModalDocument) -> MultiModalEmbedding:
        """Embed a multi-modal document.

        Args:
            document: MultiModalDocument to embed

        Returns:
            MultiModalEmbedding with embeddings for each modality
        """
        embeddings = {}

        # Embed text
        if document.text_content:
            embeddings["text"] = await self.embed_text(document.text_content)

        # Embed images
        if document.images:
            image_embeddings = []
            for image in document.images:
                img_emb = await self.embed_image(image)
                image_embeddings.append(img_emb)

            # Average image embeddings
            embeddings["image"] = np.mean(image_embeddings, axis=0).tolist()

        # Embed audio
        if document.audio:
            audio_embeddings = []
            for audio in document.audio:
                try:
                    audio_emb = await self.embed_audio(audio)
                    audio_embeddings.append(audio_emb)
                except NotImplementedError:
                    continue

            if audio_embeddings:
                embeddings["audio"] = np.mean(audio_embeddings, axis=0).tolist()

        # Embed videos
        if document.videos:
            video_embeddings = []
            for video in document.videos:
                video_emb = await self.embed_video(video)
                video_embeddings.append(video_emb)

            embeddings["video"] = np.mean(video_embeddings, axis=0).tolist()

        # Fuse embeddings
        fused = self._fuse_multimodal_embeddings(embeddings)

        return MultiModalEmbedding(
            text=embeddings.get("text"),
            image=embeddings.get("image"),
            audio=embeddings.get("audio"),
            video=embeddings.get("video"),
            fused=fused,
            fusion_method=self.fusion_method,
        )

    def _fuse_embeddings(self, embeddings: list[list[float]]) -> list[float]:
        """Fuse multiple embeddings into one.

        Args:
            embeddings: List of embedding vectors

        Returns:
            Fused embedding vector
        """
        if self.fusion_method == "concat":
            # Concatenate all embeddings
            return np.concatenate(embeddings).tolist()

        if self.fusion_method == "average":
            # Average all embeddings
            return np.mean(embeddings, axis=0).tolist()

        if self.fusion_method == "weighted":
            # Weighted average (requires same dimension)
            # Not implemented yet
            msg = "Weighted fusion not implemented"
            raise NotImplementedError(msg)

        msg = f"Unknown fusion method: {self.fusion_method}"
        raise ValueError(msg)

    def _fuse_multimodal_embeddings(
        self,
        embeddings: dict[str, list[float]],
    ) -> list[float]:
        """Fuse embeddings from different modalities.

        Args:
            embeddings: Dictionary of modality -> embedding

        Returns:
            Fused embedding vector
        """
        if not embeddings:
            return []

        # Order modalities consistently
        ordered_modalities = ["text", "image", "audio", "video"]
        available_embeddings = [
            embeddings[mod] for mod in ordered_modalities if mod in embeddings
        ]

        return self._fuse_embeddings(available_embeddings)

    def get_embedding_dimension(self, modality: Modality | None = None) -> int:
        """Get embedding dimension for a modality.

        Args:
            modality: Optional modality to get dimension for

        Returns:
            Embedding dimension
        """
        if self._clip:
            return self._clip.get_embedding_dimension()
        return 512  # Default CLIP dimension
