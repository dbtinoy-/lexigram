"""Multi-modal document types for RAG."""

from __future__ import annotations

from lexigram.ai.rag.multimodal.types.audio import AudioDocument, AudioMetadata
from lexigram.ai.rag.multimodal.types.enums import (
    AudioFormat,
    ImageFormat,
    Modality,
    VideoFormat,
)
from lexigram.ai.rag.multimodal.types.image import ImageDocument, ImageMetadata
from lexigram.ai.rag.multimodal.types.multimodal import (
    MultiModalDocument,
    MultiModalEmbedding,
)
from lexigram.ai.rag.multimodal.types.video import VideoDocument, VideoMetadata

# Resolve forward references
ImageDocument.model_rebuild()
AudioDocument.model_rebuild()
VideoDocument.model_rebuild()
MultiModalDocument.model_rebuild()

__all__ = [
    "AudioDocument",
    "AudioFormat",
    "AudioMetadata",
    "ImageDocument",
    "ImageFormat",
    "ImageMetadata",
    "Modality",
    "MultiModalDocument",
    "MultiModalEmbedding",
    "VideoDocument",
    "VideoFormat",
    "VideoMetadata",
]
