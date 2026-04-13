"""Video generation exceptions for the lexigram-multimedia-video package."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import VideoGenerationError

__all__ = [
    "VideoGenerationAuthenticationError",
    "VideoGenerationError",
    "VideoProcessingError",
    "VideoTimeoutError",
]


class VideoTimeoutError(VideoGenerationError):
    """Raised when a video generation operation exceeds its timeout."""

    _code = "LEX_ERR_MM_VIDEO_001"


class VideoGenerationAuthenticationError(VideoGenerationError):
    """Raised when the video backend rejects the configured API credentials."""

    _code = "LEX_ERR_MM_VIDEO_002"


class VideoProcessingError(VideoGenerationError):
    """Raised when an ffmpeg processing operation fails."""

    _code = "LEX_ERR_MM_VIDEO_003"
