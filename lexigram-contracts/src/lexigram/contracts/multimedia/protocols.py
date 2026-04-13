"""Structural protocols for multimedia generation providers.

Four separate Protocols rather than one shared base class — Python's
structural typing makes a base class unnecessary, and each media type's
request/response shape differs enough that a shared abstract method
signature would need to be typed loosely (``Any``) to fit all four.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexigram.contracts.core.result import Result
    from lexigram.contracts.multimedia.exceptions import (
        MultimediaError,
        VideoGenerationError,
    )
    from lexigram.contracts.multimedia.types import (
        ImageRequest,
        MediaAsset,
        MusicRequest,
        TTSRequest,
        VideoOperation,
        VideoRequest,
    )


@runtime_checkable
class TTSProvider(Protocol):
    """Protocol for text-to-speech generation backends."""

    async def generate(
        self, request: TTSRequest
    ) -> Result[MediaAsset, MultimediaError]: ...


@runtime_checkable
class MusicProvider(Protocol):
    """Protocol for music/sound generation backends."""

    async def generate(
        self, request: MusicRequest
    ) -> Result[MediaAsset, MultimediaError]: ...


@runtime_checkable
class VideoProvider(Protocol):
    """Protocol for video generation backends."""

    async def generate(
        self, request: VideoRequest
    ) -> Result[MediaAsset, MultimediaError]: ...


@runtime_checkable
class VideoProcessor(Protocol):
    """Protocol for ffmpeg-backed video processing/editing backends."""

    async def process(
        self, operation: VideoOperation
    ) -> Result[MediaAsset, VideoGenerationError]: ...


@runtime_checkable
class ImageProvider(Protocol):
    """Protocol for still-image generation backends."""

    async def generate(
        self, request: ImageRequest
    ) -> Result[MediaAsset, MultimediaError]: ...


__all__ = [
    "ImageProvider",
    "MusicProvider",
    "TTSProvider",
    "VideoProcessor",
    "VideoProvider",
]
