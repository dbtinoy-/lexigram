"""Combined multimodal document types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from lexigram.ai.rag.multimodal.types.audio import AudioDocument
from lexigram.ai.rag.multimodal.types.enums import Modality
from lexigram.ai.rag.multimodal.types.image import ImageDocument
from lexigram.ai.rag.multimodal.types.video import VideoDocument
from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False)
class MultiModalEmbedding(DomainModel):
    """Combined embeddings for multi-modal documents."""

    text: list[float] | None = None
    image: list[float] | None = None
    audio: list[float] | None = None
    video: list[float] | None = None
    fused: list[float] | None = None
    fusion_method: str = "concat"

    @property
    def available_modalities(self) -> list[Modality]:
        modalities = []
        if self.text:
            modalities.append(Modality.TEXT)
        if self.image:
            modalities.append(Modality.IMAGE)
        if self.audio:
            modalities.append(Modality.AUDIO)
        if self.video:
            modalities.append(Modality.VIDEO)
        return modalities

    @property
    def has_fused(self) -> bool:
        return self.fused is not None and len(self.fused) > 0

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": [0.1, 0.2, 0.3],
                "image": [0.4, 0.5, 0.6],
                "fused": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
                "fusion_method": "concat",
            },
        },
    }


@dataclass(init=False)
class MultiModalDocument(DomainModel):
    """Document combining multiple modalities."""

    text_content: str | None = None
    images: list[ImageDocument] = Field(default_factory=list)
    audio: list[AudioDocument] = Field(default_factory=list)
    videos: list[VideoDocument] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    embeddings: MultiModalEmbedding | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def modalities(self) -> list[Modality]:
        modalities = []
        if self.text_content:
            modalities.append(Modality.TEXT)
        if self.images:
            modalities.append(Modality.IMAGE)
        if self.audio:
            modalities.append(Modality.AUDIO)
        if self.videos:
            modalities.append(Modality.VIDEO)
        return modalities

    @property
    def is_multimodal(self) -> bool:
        return len(self.modalities) > 1

    @property
    def has_embeddings(self) -> bool:
        return self.embeddings is not None

    @property
    def total_images(self) -> int:
        return len(self.images)

    @property
    def total_audio(self) -> int:
        return len(self.audio)

    @property
    def total_videos(self) -> int:
        return len(self.videos)

    model_config = {
        "json_schema_extra": {
            "example": {
                "text_content": "Product review",
                "images": [],
                "metadata": {"source": "blog", "category": "review"},
            },
        },
    }
