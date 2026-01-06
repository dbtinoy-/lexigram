"""Loaders for multi-modal documents."""

from __future__ import annotations

from lexigram.ai.rag.multimodal.loaders.audio import AudioLoader
from lexigram.ai.rag.multimodal.loaders.image import ImageLoader
from lexigram.ai.rag.multimodal.loaders.video import VideoLoader

__all__ = [
    "AudioLoader",
    "ImageLoader",
    "VideoLoader",
]
