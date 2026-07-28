"""Audio-related document types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from lexigram.ai.rag.multimodal.types.enums import AudioFormat
from lexigram.domain import DomainModel
from lexigram.validation import Field, field_validator


@dataclass(init=False)
class AudioMetadata(DomainModel):
    """Metadata for audio documents."""

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    genre: str | None = None
    year: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    id3: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Interview Recording",
                "artist": "John Doe",
                "tags": ["interview", "tech"],
            },
        },
    }


@dataclass(init=False)
class AudioDocument(DomainModel):
    """Document representing audio content."""

    content: bytes | str
    format: AudioFormat
    duration: float = Field(gt=0)
    sample_rate: int = Field(gt=0)
    channels: int = Field(default=1, ge=1, le=8)
    metadata: AudioMetadata = Field(default_factory=AudioMetadata)
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
    def has_transcript(self) -> bool:
        return self.transcript is not None and len(self.transcript) > 0

    @property
    def has_embedding(self) -> bool:
        return self.embedding is not None and len(self.embedding) > 0

    @property
    def is_mono(self) -> bool:
        return self.channels == 1

    @property
    def is_stereo(self) -> bool:
        return self.channels == 2

    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "content": "/path/to/audio.mp3",
                "format": "mp3",
                "duration": 180.5,
                "sample_rate": 44100,
                "metadata": {"title": "Interview"},
            },
        },
    }
