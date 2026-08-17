"""Image-related document types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from lexigram.ai.rag.multimodal.types.enums import ImageFormat
from lexigram.domain import DomainModel
from lexigram.validation import Field, field_validator


@dataclass(init=False)
class ImageMetadata(DomainModel):
    """Metadata for image documents."""

    caption: str | None = None
    alt_text: str | None = None
    source: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    location: dict[str, float] | None = None
    tags: list[str] = Field(default_factory=list)
    exif: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "caption": "Sunset over mountains",
                "tags": ["landscape", "sunset"],
                "source": "https://example.com/image.jpg",
            },
        },
    }


@dataclass(init=False)
class ImageDocument(DomainModel):
    """Document representing an image."""

    content: bytes | str
    format: ImageFormat
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    metadata: ImageMetadata = Field(default_factory=ImageMetadata)
    text_content: str | None = None
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
    def has_text(self) -> bool:
        return self.text_content is not None and len(self.text_content) > 0

    @property
    def has_embedding(self) -> bool:
        return self.embedding is not None and len(self.embedding) > 0

    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "content": "/path/to/image.jpg",
                "format": "jpeg",
                "width": 1920,
                "height": 1080,
                "metadata": {"caption": "Product photo"},
            },
        },
    }
