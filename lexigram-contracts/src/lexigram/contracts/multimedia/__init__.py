"""Multimedia generation contracts — audio, music, video, image."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import (
    ImageGenerationError,
    MultimediaError,
    MusicGenerationError,
    ProviderNotInstalledError,
    TTSError,
    VideoGenerationError,
)
from lexigram.contracts.multimedia.protocols import (
    ImageProvider,
    MusicProvider,
    TTSProvider,
    VideoProvider,
)
from lexigram.contracts.multimedia.types import (
    ImageRequest,
    MediaAsset,
    MusicRequest,
    TTSRequest,
    VideoRequest,
)

__all__ = [
    "ImageGenerationError",
    "ImageProvider",
    "ImageRequest",
    "MediaAsset",
    "MultimediaError",
    "MusicGenerationError",
    "MusicProvider",
    "MusicRequest",
    "ProviderNotInstalledError",
    "TTSError",
    "TTSProvider",
    "TTSRequest",
    "VideoGenerationError",
    "VideoProvider",
    "VideoRequest",
]
