"""Video generation exceptions for the lexigram-multimedia-video package."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import VideoGenerationError

__all__ = [
    "VideoGenerationAuthenticationError",
    "VideoGenerationError",
    "VideoTimeoutError",
]


class VideoTimeoutError(VideoGenerationError):
    """Raised when a video generation operation exceeds its timeout."""

    code = "LEX_ERR_MM_VIDEO_001"


class VideoGenerationAuthenticationError(VideoGenerationError):
    """Raised when the video backend rejects the configured API credentials."""

    code = "LEX_ERR_MM_VIDEO_002"
