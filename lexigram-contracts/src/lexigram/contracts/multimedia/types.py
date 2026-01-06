"""Value objects for the multimedia generation contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MediaAsset:
    """Result of a generation call — carries either raw bytes or a URI, never both.

    Several v1 providers (ElevenLabs, OpenAI TTS, Stability) return raw bytes
    in the response body with no hosted URL, so callers must check
    :attr:`has_bytes`/:attr:`has_uri` rather than assuming a shape.
    """

    mime_type: str
    provider: str
    bytes_data: bytes | None = None
    uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_bytes(self) -> bool:
        return self.bytes_data is not None

    @property
    def has_uri(self) -> bool:
        return self.uri is not None


@dataclass(frozen=True)
class TTSRequest:
    text: str
    voice: str | None = None
    format: str = "mp3"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MusicRequest:
    prompt: str
    duration_seconds: float = 30.0
    format: str = "mp3"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VideoRequest:
    prompt: str
    duration_seconds: float = 4.0
    resolution: str = "1280x720"
    image_uri: str | None = None
    format: str = "mp4"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ImageRequest:
    prompt: str
    width: int = 1024
    height: int = 1024
    format: str = "png"
    extra: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "ImageRequest",
    "MediaAsset",
    "MusicRequest",
    "TTSRequest",
    "VideoRequest",
]
