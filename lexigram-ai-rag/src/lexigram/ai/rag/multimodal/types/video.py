"""Video-related document types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lexigram.domain import DomainModel
from lexigram.validation import Field, field_validator

if TYPE_CHECKING:
    from datetime import datetime

    from lexigram.ai.rag.multimodal.types.audio import AudioDocument
    from lexigram.ai.rag.multimodal.types.enums import VideoFormat
    from lexigram.ai.rag.multimodal.types.image import ImageDocument


@dataclass(init=False)
class VideoMetadata(DomainModel):
    """Metadata for video documents."""

    title: str | None = None
    description: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    codec: str | None = None
    bitrate: int | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Product Demo",
                "tags": ["demo", "product"],
                "chapters": [{"time": 0, "title": "Introduction"}],
            },
        },
    }


@dataclass(init=False)
class VideoDocument(DomainModel):
    """Document representing video content."""

    content: bytes | str
    format: VideoFormat
    duration: float = Field(gt=0)
    fps: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    metadata: VideoMetadata = Field(default_factory=VideoMetadata)
    frames: list[ImageDocument] = Field(default_factory=list)
    audio_track: AudioDocument | None = None
    transcript: str | None = None
    embedding: list[float] | None = None
    file_path: Path | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: bytes | str) -> bytes | str:
        if isinstance(v, str):
            path = Path(v)
            if not path.exists():
                raise ValueError(f"File path does not exist: {v}")
        return v

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    @property
    def total_frames(self) -> int:
        return int(self.duration * self.fps)

    @property
    def has_audio(self) -> bool:
        return self.audio_track is not None

    @property
    def has_transcript(self) -> bool:
        return self.transcript is not None and len(self.transcript) > 0

    @property
    def has_frames(self) -> bool:
        return len(self.frames) > 0

    @property
    def has_embedding(self) -> bool:
        return self.embedding is not None and len(self.embedding) > 0

    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "content": "/path/to/video.mp4",
                "format": "mp4",
                "duration": 300.0,
                "fps": 30.0,
                "width": 1920,
                "height": 1080,
                "metadata": {"title": "Tutorial Video"},
            },
        },
    }
