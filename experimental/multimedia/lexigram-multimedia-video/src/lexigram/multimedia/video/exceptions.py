"""Video generation exceptions for the lexigram-multimedia-video package."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import VideoGenerationError

__all__ = [
    "VideoAssetDownloadError",
    "VideoAssetTooLargeError",
    "VideoGenerationAuthenticationError",
    "VideoGenerationError",
    "VideoProcessingError",
    "VideoTimeoutError",
    "VideoUnsafeAssetURLError",
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


class VideoAssetTooLargeError(VideoProcessingError, ValueError):
    """Raised when a materialized asset exceeds the byte cap.

    Also a ``ValueError`` so the processor's existing ``(OSError, ValueError)``
    Result wrapping converts the failure to ``Err``.
    """

    _code = "LEX_ERR_MM_VIDEO_004"

    def __init__(self, max_bytes: int) -> None:
        super().__init__(f"asset bytes too large: exceeds {max_bytes} byte cap")


class VideoUnsafeAssetURLError(VideoProcessingError, ValueError):
    """Raised when an asset URI is not safe to request.

    Also a ``ValueError`` so the processor's existing ``(OSError, ValueError)``
    Result wrapping converts the failure to ``Err``.
    """

    _code = "LEX_ERR_MM_VIDEO_005"

    def __init__(self, uri: str) -> None:
        super().__init__(f"unsafe asset URL: {uri!r}")


class VideoAssetDownloadError(VideoProcessingError, ValueError):
    """Raised when a remote asset download returns a non-200 response.

    Also a ``ValueError`` so the processor's existing ``(OSError, ValueError)``
    Result wrapping converts the failure to ``Err``.
    """

    _code = "LEX_ERR_MM_VIDEO_006"

    def __init__(self, status: int) -> None:
        super().__init__(f"asset download failed: HTTP {status}")
