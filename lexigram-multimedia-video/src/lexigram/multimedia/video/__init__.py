"""Video generation subsystem for the Lexigram multimedia package family."""

from __future__ import annotations

from lexigram.multimedia.video.config import VideoConfig, VideoProcessingConfig
from lexigram.multimedia.video.di import VideoGenerationProvider
from lexigram.multimedia.video.exceptions import (
    VideoGenerationAuthenticationError,
    VideoGenerationError,
    VideoTimeoutError,
)
from lexigram.multimedia.video.module import VideoModule
from lexigram.multimedia.video.processing import FFmpegVideoProcessor
from lexigram.multimedia.video.providers import (
    LocalHttpVideoProvider,
    OpenAIVideoProvider,
    RunwayVideoProvider,
    Wan22VideoProvider,
)
from lexigram.multimedia.video.tasks import VideoGenerationTask, VideoProcessingTask

__all__ = [
    "FFmpegVideoProcessor",
    "LocalHttpVideoProvider",
    "OpenAIVideoProvider",
    "RunwayVideoProvider",
    "VideoConfig",
    "VideoGenerationAuthenticationError",
    "VideoGenerationError",
    "VideoGenerationProvider",
    "VideoGenerationTask",
    "VideoModule",
    "VideoProcessingConfig",
    "VideoProcessingTask",
    "VideoTimeoutError",
    "Wan22VideoProvider",
]
