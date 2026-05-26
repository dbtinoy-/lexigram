"""Video frame-rate interpolation subsystem for the Lexigram multimedia package family."""

from __future__ import annotations

from lexigram.multimedia.interpolate.config import InterpolationConfig
from lexigram.multimedia.interpolate.di import InterpolationGenerationProvider
from lexigram.multimedia.interpolate.module import InterpolationModule
from lexigram.multimedia.interpolate.providers import RifeInterpolationProvider
from lexigram.multimedia.interpolate.tasks import InterpolationTask
from lexigram.multimedia.interpolate.video_interpolation_service import (
    VideoInterpolationService,
)

__all__ = [
    "InterpolationConfig",
    "InterpolationGenerationProvider",
    "InterpolationModule",
    "InterpolationTask",
    "RifeInterpolationProvider",
    "VideoInterpolationService",
]
