"""Embeddings for multi-modal documents."""

from __future__ import annotations

from lexigram.ai.rag.multimodal.embeddings.clip import CLIPEmbedding
from lexigram.ai.rag.multimodal.embeddings.multimodal import (
    MultiModalEmbedder,
)

__all__ = [
    "CLIPEmbedding",
    "MultiModalEmbedder",
]
