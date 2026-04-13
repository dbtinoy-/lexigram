"""Value objects for the multimedia generation contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


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


OverlayPosition = Literal[
    "top",
    "bottom",
    "center",
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
]


@dataclass(frozen=True)
class TransitionSpec:
    kind: Literal["cut", "crossfade"]
    duration: float = 0.5


@dataclass(frozen=True)
class SubtitleCue:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Trim:
    asset: MediaAsset
    start: float
    end: float


@dataclass(frozen=True)
class Concat:
    assets: list[MediaAsset]
    transitions: list[TransitionSpec] | None = None


@dataclass(frozen=True)
class OverlayText:
    asset: MediaAsset
    text: str
    position: OverlayPosition
    start: float | None = None
    end: float | None = None
    font_size: int = 32
    color: str = "white"


@dataclass(frozen=True)
class OverlayImage:
    asset: MediaAsset
    image_asset: MediaAsset
    position: OverlayPosition
    opacity: float = 1.0
    start: float | None = None
    end: float | None = None


@dataclass(frozen=True)
class BurnSubtitles:
    asset: MediaAsset
    cues: list[SubtitleCue]


@dataclass(frozen=True)
class MuxAudio:
    asset: MediaAsset
    audio_asset: MediaAsset
    mode: Literal["replace", "mix"]
    music_volume: float = 1.0
    duck_under_existing: bool = False


@dataclass(frozen=True)
class ExtractThumbnail:
    asset: MediaAsset
    timestamp: float


@dataclass(frozen=True)
class ToGif:
    asset: MediaAsset
    start: float | None = None
    end: float | None = None
    fps: int = 10
    width: int = 480


@dataclass(frozen=True)
class Transcode:
    asset: MediaAsset
    format: str
    codec: str | None = None
    resolution: str | None = None
    bitrate: str | None = None


@dataclass(frozen=True)
class ChangeSpeed:
    asset: MediaAsset
    factor: float


@dataclass(frozen=True)
class Crop:
    asset: MediaAsset
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class ColorFilter:
    asset: MediaAsset
    preset: Literal["none", "grayscale", "sepia", "vintage"] | None = None
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0


@dataclass(frozen=True)
class RawFilter:
    assets: list[MediaAsset]
    filter_complex: str
    maps: list[str]
    extra_args: list[str] = field(default_factory=list)


VideoOperation = (
    Trim
    | Concat
    | OverlayText
    | OverlayImage
    | BurnSubtitles
    | MuxAudio
    | ExtractThumbnail
    | ToGif
    | Transcode
    | ChangeSpeed
    | Crop
    | ColorFilter
    | RawFilter
)


__all__ = [
    "BurnSubtitles",
    "ChangeSpeed",
    "ColorFilter",
    "Concat",
    "Crop",
    "ExtractThumbnail",
    "ImageRequest",
    "MediaAsset",
    "MusicRequest",
    "MuxAudio",
    "OverlayImage",
    "OverlayPosition",
    "OverlayText",
    "RawFilter",
    "SubtitleCue",
    "TTSRequest",
    "ToGif",
    "Transcode",
    "TransitionSpec",
    "Trim",
    "VideoOperation",
    "VideoRequest",
]
